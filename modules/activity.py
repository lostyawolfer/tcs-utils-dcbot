import asyncio

import discord
from discord import AllowedMentions
from modules import config, general
from modules.general import has_role, send, count_available, count_in_vc, emojify
from modules.role_management import RoleSession
import datetime
from modules.bot_init import bot


async def voice_check(rs: RoleSession, member: discord.Member) -> None:
    async def check(vc: str, vc_role: str, vc_leader_role: str, reverse_role: str, join_msg_id: str, leave_msg_id: str,
                    color: str = 'g'):
        channel = member.guild.get_channel(config.channels[vc])
        members = await count_in_vc(bot, vc)

        if member.voice and member.voice.channel == channel:
            if not has_role(member, config.roles[vc_role]):
                await send(bot, config.message(join_msg_id, member=member.display_name,
                                               count=f'{emojify(f'{members}', f'{color}')}'))
            if has_role(member, config.roles['leader']):
                rs.add(config.roles[vc_leader_role])
            rs.add(config.roles[vc_role])
            rs.remove(config.roles[reverse_role])

        else:
            if has_role(member, config.roles[vc_role]):
                await send(bot, config.message(leave_msg_id, member=member.display_name,
                                               count=f'{emojify(f'{members}', f'{color}')}'))
            rs.remove(config.roles[vc_role])
            rs.remove(config.roles[vc_leader_role])
            if has_role(member, config.roles['available']):
                rs.add(config.roles[reverse_role])

    await check('vc', 'in_vc', 'in_vc_leader', 'available_not_in_vc',
                'join_vc', 'leave_vc')

    await check('vc2', 'in_vc_2', 'in_vc_2_leader', 'available_not_in_vc_2',
                'join_vc_2', 'leave_vc_2', 'p')

    await check('vc3', 'in_vc_3', 'in_vc_3_leader', 'available_not_in_vc_3',
                'join_vc_3', 'leave_vc_3', 'r')



async def add_availability(rs: RoleSession, member: discord.Member) -> None:
    if not has_role(member, config.roles['available']):
        available_people = await count_available(member.guild)
        if available_people >= 8:
            await send(
                config.message(
                    'available_ping',
                    name=member.mention,
                    available_count=f"{emojify(f'{available_people}', 'b')}",
                ),
                pings=AllowedMentions(users=False, roles=True),
            )
        else:
            await send(
                config.message(
                    'available',
                    name=member.mention,
                    available_count=f"{emojify(f'{available_people}', 'b')}",
                ),
                pings=AllowedMentions.none(),
            )

    rs.add('available')
    rs.remove('not_available')

    msg = await member.guild.get_channel(
        config.channels['availability']
    ).fetch_message(config.channels['availability_message'])

    await msg.remove_reaction(
        discord.PartialEmoji(
            id=config.channels['availability_reaction'],
            name='available',
        ),
        member.guild.me
    )


async def remove_availability(rs: RoleSession, member: discord.Member) -> None:
    guild = member.guild
    available_people = await count_available(guild)

    if has_role(member, config.roles['available']):
        await send(
            config.message(
                'unavailable',
                name=member.mention,
                available_count=f"{emojify(f'{available_people}', 'b')}",
            ),
            pings=AllowedMentions.none()
        )

    rs.remove('available')
    rs.add('not_available')

    if available_people == 0:
        msg = await member.guild.get_channel(
            config.channels['availability']
        ).fetch_message(config.channels['availability_message'])

        await msg.add_reaction(
            discord.PartialEmoji(
                id=config.channels['availability_reaction'],
                name='available',
            )
        )


async def availability_check(rs: RoleSession, member: discord.Member) -> None:
    channel = member.guild.get_channel(config.channels['availability'])
    try:
        msg = await channel.fetch_message(config.channels['availability_message'])
    except (discord.NotFound, discord.Forbidden):
        return

    found_reaction = None
    for reaction in msg.reactions:
        if reaction.emoji.id == config.channels['availability_reaction']:
            found_reaction = reaction
            break

    if found_reaction:
        async for user in found_reaction.users():
            if user == member:
                await add_availability(rs, member)
                return
        await remove_availability(rs, member)



def check_member_join_date(member: discord.Member) -> int | None:
    days = None
    if member.guild.get_role(config.roles['newbie']) in member.roles:
        if member.joined_at:
            now = datetime.datetime.now(member.joined_at.tzinfo)
            time_since_join = now - member.joined_at
            days = time_since_join.days
    return days


async def full_check_member(rs: RoleSession, member: discord.Member) -> None:
    await availability_check(rs, member)
    await voice_check(rs, member)
    days = check_member_join_date(member)
    if days is not None and days > 7:
        rs.remove('newbie')


async def check_all_members() -> None:
    server = bot.get_guild(config.TARGET_GUILD)
    await server.chunk()
    total_members = server.member_count
    member_n = 0
    members = server.members
    for member in members:
        member_n += 1
        percent = round(member_n * 100 / total_members, 1)
        if not member.bot:
            async with RoleSession(member) as rs:
                await full_check_member(rs, member)
        print(f'checking members - {percent}')

    await general.update_status(status=discord.Status.online) # type: ignore


last_activity_cache = {}


def update_cache(member_id: int, ts: float = None):
    last_activity_cache[member_id] = ts or discord.utils.utcnow().timestamp()


async def build_activity_cache():
    """runs once on startup to prevent false positives"""
    guild = bot.get_guild(config.TARGET_GUILD)
    chat = bot.get_channel(config.channels['chat'])

    print("building activity cache...")
    # 10k should be enough to cover the last week of activity
    async for msg in chat.history(limit=10000):
        ts = msg.created_at.timestamp()

        # update for the author
        if not msg.author.bot:
            if ts > last_activity_cache.get(msg.author.id, 0):
                update_cache(msg.author.id, ts)

        # check for bot mentions (vc logs, joins, etc)
        elif msg.author == bot.user:
            for mention in msg.mentions:
                if ts > last_activity_cache.get(mention.id, 0):
                    update_cache(mention.id, ts)
    print(f"cache built. tracked {len(last_activity_cache)} members.")


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

        # we only open a session if we actually need to change something
        needs_inactive = not general.has_role(m, config.roles['inactive']) and last_ts < cutoff_6d
        needs_unavail = general.has_role(m, config.roles['available']) and last_ts < cutoff_1h

        if needs_inactive or needs_unavail:
            async with RoleSession(m) as rs:
                if needs_unavail:
                    if not availability_msg:
                        ch = guild.get_channel(config.channels['availability'])
                        availability_msg = await ch.fetch_message(config.channels['availability_message'])

                    rs.remove('available')
                    await availability_msg.remove_reaction(
                        discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), m
                    )
                    await general.send(config.message('unavailable_auto_bot', name=m.mention,
                                                      available_count=f"{general.emojify(str(await m.count_available(bot)), 'b')}"),
                                       pings=discord.AllowedMentions.none())

                if needs_inactive:
                    rs.add('inactive')
                    rs.remove('person')

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

    # clear changes before processing to avoid race conditions
    user_pending_changes.pop(user_id)

    member = guild.get_member(user_id)
    if not member: return

    # we get the current roles once to compare against
    current_role_ids = {r.id for r in member.roles}

    # find all possible "interested" roles across all tiered messages
    all_interested_roles = []
    for mid in [INTERESTED_MESSAGE_BASE, INTERESTED_MESSAGE_STAR, INTERESTED_MESSAGE_ULTIMATE]:
        all_interested_roles.extend(get_interested_role_map(guild, mid).values())

    # get the current reaction state for the user across those messages
    # this is the "source of truth" for what they want
    desired_role_ids = set()
    for mid in [INTERESTED_MESSAGE_BASE, INTERESTED_MESSAGE_STAR, INTERESTED_MESSAGE_ULTIMATE]:
        try:
            channel = guild.get_channel(INTERESTED_CHANNEL_ID)
            msg = await channel.fetch_message(mid)
            role_map = get_interested_role_map(guild, mid)
            for reaction in msg.reactions:
                emoji_str = str(reaction.emoji)
                if emoji_str in role_map:
                    async for user in reaction.users():
                        if user.id == user_id:
                            desired_role_ids.add(role_map[emoji_str].id)
                            break
        except:
            continue

    # calculate what actually needs to change relative to current server state
    to_add = []
    to_remove = []

    async with RoleSession(member) as rs:
        for role in all_interested_roles:
            is_active = role.id in current_role_ids
            should_be_active = role.id in desired_role_ids

            if should_be_active and not is_active:
                rs.add(role.id)
                to_add.append(role)
            elif not should_be_active and is_active:
                rs.remove(role.id)
                to_remove.append(role)

    # logic for formatting and sending messages remains same,
    # but now it only triggers if there's a real difference from the start of the 5s window
    def format_names(roles):
        names = [f"**{r.name.split('interested in ')[-1]}**" for r in roles]
        if len(names) > 1:
            return f"{', '.join(names[:-1])} and {names[-1]}"
        return names[0]

    output = []
    if to_remove:
        output.append(
            f"<:no_multiplayer:1463357263811973303> {member.mention} is no longer interested in {format_names(to_remove)}")
    if to_add:
        output.append(
            f"<:yes_multiplayer:1463357364110495754> {member.mention} is now interested in {format_names(to_add)}")

    if output:
        await general.send('\n'.join(output), pings=AllowedMentions.none())


async def schedule_interested_debounce(user_id: int, guild: discord.Guild):
    if user_id in user_debounce_tasks:
        user_debounce_tasks[user_id].cancel()

    async def wait():
        await asyncio.sleep(5)
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