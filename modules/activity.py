import asyncio
import datetime
import discord

from discord import AllowedMentions
from modules import config, general
from modules.role_management import RoleSession
from modules.general import (
    count_available,
    count_in_vc,
    emojify,
)
from modules.bot_init import bot


# ============================================================
# activity cache
# ============================================================

last_activity_cache: dict[int, float] = {}


def update_cache(member_id: int, ts: float | None = None):
    last_activity_cache[member_id] = ts or discord.utils.utcnow().timestamp()


async def build_activity_cache():
    guild = bot.get_guild(config.TARGET_GUILD)
    chat = bot.get_channel(config.channels["chat"])

    async for msg in chat.history(limit=10_000):
        ts = msg.created_at.timestamp()

        if not msg.author.bot:
            if ts > last_activity_cache.get(msg.author.id, 0):
                update_cache(msg.author.id, ts)

        elif msg.author == bot.user:
            for mention in msg.mentions:
                if ts > last_activity_cache.get(mention.id, 0):
                    update_cache(mention.id, ts)


# ============================================================
# pure state computation
# ============================================================

async def compute_availability(member: discord.Member) -> bool:
    channel = member.guild.get_channel(config.channels["availability"])
    try:
        msg = await channel.fetch_message(
            config.channels["availability_message"]
        )
    except (discord.NotFound, discord.Forbidden):
        return False

    for reaction in msg.reactions:
        if reaction.emoji.id == config.channels["availability_reaction"]:
            async for user in reaction.users():
                if user.id == member.id:
                    return True
            break

    return False


def compute_vc_state(member: discord.Member) -> dict[str, bool]:
    state = {"vc": False, "vc2": False, "vc3": False}

    if member.voice and member.voice.channel:
        for key in state:
            if member.voice.channel.id == config.channels[key]:
                state[key] = True

    return state


def check_member_join_date(member: discord.Member) -> int | None:
    if member.guild.get_role(config.roles["newbie"]) not in member.roles:
        return None

    if not member.joined_at:
        return None

    now = datetime.datetime.now(member.joined_at.tzinfo)
    return (now - member.joined_at).days


# ============================================================
# reconciliation (mutation only, no messaging)
# ============================================================

def reconcile_availability(rs: RoleSession, is_available: bool):
    if is_available:
        rs.add("available")
        rs.remove("not_available")
    else:
        rs.remove("available")
        rs.add("not_available")


def reconcile_vc_roles(
    rs: RoleSession,
    member: discord.Member,
    vc_state: dict[str, bool],
):
    mapping = {
        "vc":  ("in_vc",   "in_vc_leader",   "available_not_in_vc"),
        "vc2": ("in_vc_2", "in_vc_2_leader", "available_not_in_vc_2"),
        "vc3": ("in_vc_3", "in_vc_3_leader", "available_not_in_vc_3"),
    }

    is_leader = general.has_role(member, config.roles["leader"])
    is_available = general.has_role(member, config.roles["available"])

    for key, (vc_role, leader_role, reverse_role) in mapping.items():
        if vc_state[key]:
            rs.add(vc_role)
            rs.remove(reverse_role)
            if is_leader:
                rs.add(leader_role)
        else:
            rs.remove(vc_role)
            rs.remove(leader_role)
            if is_available:
                rs.add(reverse_role)


# ============================================================
# checker core
# ============================================================

def snapshot_roles(member: discord.Member) -> set[int]:
    return {r.id for r in member.roles}


async def full_check_member(member: discord.Member):
    before = snapshot_roles(member)

    is_available = await compute_availability(member)
    vc_state = compute_vc_state(member)
    days = check_member_join_date(member)

    async with RoleSession(member) as rs:
        reconcile_availability(rs, is_available)
        reconcile_vc_roles(rs, member, vc_state)

        if days is not None and days > 7:
            rs.remove("newbie")

    fresh = member.guild.get_member(member.id)
    if not fresh:
        return None

    after = snapshot_roles(fresh)
    return before, after


# ============================================================
# announcements (checker-specific)
# ============================================================

async def announce_availability_diff(
    member: discord.Member,
    before: set[int],
    after: set[int],
):
    avail = config.roles["available"]

    if avail not in before and avail in after:
        count = await count_available(member.guild)
        await general.send(
            config.message(
                "available",
                name=member.mention,
                available_count=emojify(str(count), "b"),
            ),
            pings=AllowedMentions.none(),
        )

    elif avail in before and avail not in after:
        count = await count_available(member.guild)
        await general.send(
            config.message(
                "unavailable",
                name=member.mention,
                available_count=emojify(str(count), "b"),
            ),
            pings=AllowedMentions.none(),
        )


# ============================================================
# public checker entrypoints
# ============================================================

async def check_all_members():
    guild = bot.get_guild(config.TARGET_GUILD)
    await guild.chunk()

    for member in guild.members:
        if member.bot:
            continue

        diff = await full_check_member(member)
        if not diff:
            continue

        before, after = diff
        if before != after:
            await announce_availability_diff(member, before, after)

    await general.update_status(status=discord.Status.online)


async def run_activity_checks():
    guild = bot.get_guild(config.TARGET_GUILD)
    now = discord.utils.utcnow().timestamp()

    cutoff_6d = now - (6 * 24 * 60 * 60)
    cutoff_1h = now - (1.5 * 60 * 60)

    availability_msg = None

    for m in guild.members:
        if m.bot or (m.voice and m.voice.channel):
            continue

        last_ts = last_activity_cache.get(m.id, 0)

        needs_inactive = (
            not general.has_role(m, config.roles["inactive"])
            and last_ts < cutoff_6d
        )
        needs_unavail = (
            general.has_role(m, config.roles["available"])
            and last_ts < cutoff_1h
        )

        if not needs_inactive and not needs_unavail:
            continue

        async with RoleSession(m) as rs:
            if needs_unavail:
                rs.remove("available")
                rs.add("not_available")

                if not availability_msg:
                    ch = guild.get_channel(config.channels["availability"])
                    availability_msg = await ch.fetch_message(
                        config.channels["availability_message"]
                    )

                await availability_msg.remove_reaction(
                    discord.PartialEmoji(
                        id=config.channels["availability_reaction"],
                        name="available",
                    ),
                    m,
                )

                count = await count_available(guild)
                await general.send(
                    config.message(
                        "unavailable_auto_bot",
                        name=m.mention,
                        available_count=emojify(str(count), "b"),
                    ),
                    pings=AllowedMentions.none(),
                )

            if needs_inactive:
                rs.add("inactive")
                rs.remove("person")

    await general.update_status()