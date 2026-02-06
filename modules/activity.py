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

    async for msg in chat.history(limit=10000):
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


INTERESTED_PREFIX = "🎮 interested in "
INTERESTED_PREFIX_BASE = "🎮🟢 interested in "
INTERESTED_PREFIX_STAR = "🎮⭐ interested in "
INTERESTED_PREFIX_ULTIMATE = "🎮☄️ interested in "

INTERESTED_CHANNEL_ID = 1464608724667858975
INTERESTED_MESSAGE_BASE = 1464609114612302035
INTERESTED_MESSAGE_STAR = 1467834855315210376
INTERESTED_MESSAGE_ULTIMATE = 1467834856640745542

user_pending_changes = {}
user_debounce_tasks = {}
user_initial_states = {}

def get_interested_role_map(guild: discord.Guild, message_id: int):
    role_map = {}
    if message_id == INTERESTED_MESSAGE_BASE:
        prefixes = [INTERESTED_PREFIX_BASE, INTERESTED_PREFIX]
    elif message_id == INTERESTED_MESSAGE_STAR:
        prefixes = [INTERESTED_PREFIX_STAR]
    elif message_id == INTERESTED_MESSAGE_ULTIMATE:
        prefixes = [INTERESTED_PREFIX_ULTIMATE]
    else:
        return role_map

    for role in guild.roles:
        suffix = None
        for p in prefixes:
            if role.name.startswith(p):
                suffix = role.name.replace(p, "").strip().lower()
                break

        if not suffix: continue

        if suffix == "miscellaneous hosts":
            role_map["🎮"] = role
            continue

        # remove any char that isn't a letter, number, or space, then swap spaces for underscores
        clean_suffix = "".join(c for c in suffix if c.isalnum() or c.isspace())
        emoji_name = f"badge_{clean_suffix.replace(' ', '_')}"
        emoji = discord.utils.get(guild.emojis, name=emoji_name)
        if emoji:
            role_map[str(emoji)] = role
    return role_map


async def process_interested_changes(user_id: int, guild: discord.Guild):
    if user_id not in user_pending_changes: return

    changes = user_pending_changes.pop(user_id)
    initial = user_initial_states.pop(user_id, set())

    # calculate net changes from initial state
    final_roles = (initial | changes['added']) - changes['removed']
    net_added = final_roles - initial
    net_removed = initial - final_roles

    member = guild.get_member(user_id)
    if not member or (not net_added and not net_removed): return

    # now commit the actual role changes
    async with RoleSession(member) as rs:
        for role in net_added:
            rs.add(role.id)
        for role in net_removed:
            rs.remove(role.id)

    def format_names(roles):
        names = [f"**{r.name.split('interested in ')[-1]}**" for r in roles]
        if len(names) > 1:
            return f"{', '.join(names[:-1])} and {names[-1]}"
        return names[0]

    output = []
    if net_removed:
        output.append(
            f"<:no_multiplayer:1463357263811973303> {member.mention} is no longer interested in {format_names(net_removed)}")
    if net_added:
        output.append(
            f"<:yes_multiplayer:1463357364110495754> {member.mention} is now interested in {format_names(net_added)}")

    if output:
        await general.send('\n'.join(output), pings=AllowedMentions.none())


async def schedule_interested_debounce(user_id: int, guild: discord.Guild):
    if user_id in user_debounce_tasks:
        user_debounce_tasks[user_id].cancel()

    async def wait():
        await asyncio.sleep(7)
        await process_interested_changes(user_id, guild)
        user_debounce_tasks.pop(user_id, None)

    user_debounce_tasks[user_id] = asyncio.create_task(wait())


async def sync_interested_reactions():
    guild = bot.get_guild(config.TARGET_GUILD)
    channel = guild.get_channel(INTERESTED_CHANNEL_ID)
    if not channel: return

    for mid in [INTERESTED_MESSAGE_BASE, INTERESTED_MESSAGE_STAR, INTERESTED_MESSAGE_ULTIMATE]:
        try:
            msg = await channel.fetch_message(mid)
            role_map = get_interested_role_map(guild, mid)

            # sort the items by role position (descending) to get the correct visual order
            # higher position in discord role list = "later" in the channel role list
            # usually role lists are: [Newest/Top] ... [Oldest/Bottom]
            # but for display purposes we want them in the order they appear in the map
            # which is determined by the order we find them in guild.roles
            sorted_emojis = sorted(
                role_map.keys(),
                key=lambda e: role_map[e].position,
                reverse=True
            )

            existing = [str(r.emoji) for r in msg.reactions if r.me]
            for emoji_str in sorted_emojis:
                if emoji_str not in existing:
                    await msg.add_reaction(emoji_str)
        except Exception as e:
            print(f"sync error for {mid}: {e}")