import asyncio
import discord
from discord.ext import commands
from modules import config, general
from modules.general import has_role, send, add_role, remove_role, count_available, count_in_vc, emojify


async def voice_check(bot: commands.Bot, member: discord.Member) -> None:
    async def check(vc: str, vc_role: str, vc_leader_role: str, reverse_role: str, join_msg_id: str, leave_msg_id: str,
                    not_available_role: str, color: str = 'g'):
        channel = member.guild.get_channel(config.channels[vc])
        members = await count_in_vc(bot, vc)

        if member.voice and member.voice.channel == channel:
            if not has_role(member, config.roles[vc_role]):
                await send(bot, config.message(join_msg_id, name=member.display_name,
                                               count=f'{emojify(f'{members}', f'{color}')}'))
            if not has_role(member, config.roles['available']):
                await add_role(member, config.roles[not_available_role])
            if has_role(member, config.roles['leader']):
                await add_role(member, config.roles[vc_leader_role])
            await add_role(member, config.roles[vc_role])
            await remove_role(member, config.roles[reverse_role])

        else:
            if has_role(member, config.roles[vc_role]):
                await send(bot, config.message(leave_msg_id, name=member.display_name,
                                               count=f'{emojify(f'{members}', f'{color}')}'))
            await remove_role(member, config.roles[vc_role])
            await remove_role(member, config.roles[vc_leader_role])
            await remove_role(member, config.roles[not_available_role])
            if has_role(member, config.roles['available']):
                await add_role(member, config.roles[reverse_role])

    await check('vc', 'in_vc', 'in_vc_leader', 'available_not_in_vc',
                'join_vc', 'leave_vc', 'in_vc_not_available')

    await check('vc2', 'in_vc_2', 'in_vc_2_leader', 'available_not_in_vc_2',
                'join_vc_2', 'leave_vc_2', 'in_vc_2_not_available', 'p')

    await check('vc3', 'in_vc_3', 'in_vc_3_leader', 'available_not_in_vc_3',
                'join_vc_3', 'leave_vc_3', 'in_vc_3_not_available', 'r')


async def add_availability(bot: commands.Bot, member: discord.Member) -> None:
    if not has_role(member, config.roles['available']):
        available_people = await count_available(bot)
        if available_people >= 8:
            await send(bot, config.message('available_ping', name=member.display_name,
                                           available_count=f'{emojify(f'{available_people}', 'b')}'))
        else:
            await send(bot, config.message('available', name=member.display_name,
                                           available_count=f'{emojify(f'{available_people}', 'b')}'))

    if has_role(member, config.roles['leader']):
        await add_role(member, config.roles['available_leader'])

    if has_role(member, config.roles['in_vc']):
        await remove_role(member, config.roles['available_not_in_vc'])
    else:
        await add_role(member, config.roles['available_not_in_vc'])

    if has_role(member, config.roles['in_vc_2']):
        await remove_role(member, config.roles['available_not_in_vc_2'])
    else:
        await add_role(member, config.roles['available_not_in_vc_2'])

    if has_role(member, config.roles['in_vc_3']):
        await remove_role(member, config.roles['available_not_in_vc_3'])
    else:
        await add_role(member, config.roles['available_not_in_vc_3'])

    await add_role(member, config.roles['available'])
    await remove_role(member, config.roles['not_available'])

    msg = await member.guild.get_channel(config.channels['availability']).fetch_message(
        config.channels['availability_message'])
    await msg.remove_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'),
                              member.guild.me)


async def remove_availability(bot: commands.Bot, member: discord.Member) -> None:
    available_people = await count_available(bot)
    if has_role(member, config.roles['available']):
        if available_people >= 8:
            await send(bot, config.message('unavailable_ping', name=member.display_name,
                                           available_count=f'{emojify(f'{available_people}', 'b')}'))
        else:
            await send(bot, config.message('unavailable', name=member.display_name,
                                           available_count=f'{emojify(f'{available_people}', 'b')}'))

    await remove_role(member, config.roles['available'])
    await remove_role(member, config.roles['available_leader'])
    await add_role(member, config.roles['not_available'])
    await remove_role(member, config.roles['available_not_in_vc'])
    await remove_role(member, config.roles['available_not_in_vc_2'])
    await remove_role(member, config.roles['available_not_in_vc_3'])

    if available_people == 0:
        msg = await member.guild.get_channel(config.channels['availability']).fetch_message(
            config.channels['availability_message'])
        await msg.add_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'))


async def availability_check(bot: commands.Bot, member: discord.Member) -> None:
    channel = bot.get_channel(config.channels['availability'])
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
                await add_availability(bot, member)
                return
        await remove_availability(bot, member)


async def check_role_category(member: discord.Member, category_name: str) -> None:
    for role in member.roles:
        if role.id in config.roles[f'category:{category_name}']['other']:
            await remove_role(member, config.roles[f'category:{category_name}']['none'])
            break
    else:
        await add_role(member, config.roles[f'category:{category_name}']['none'])


async def enforce_person_inactive_exclusivity(member: discord.Member) -> None:
    """Ensure person and inactive roles are mutually exclusive."""
    has_person = has_role(member, config.roles['person'])
    has_inactive = has_role(member, config.roles['inactive'])

    if has_person and has_inactive:
        await remove_role(member, config.roles['person'])

    if not has_inactive and not has_person:
        await add_role(member, config.roles['person'])


import datetime


async def check_member_join_date(bot: commands.Bot, member: discord.Member) -> None:
    if bot.get_guild(config.TARGET_GUILD).get_role(config.roles['newbie']) in member.roles:
        if member.joined_at:
            now = datetime.datetime.now(member.joined_at.tzinfo)
            time_since_join = now - member.joined_at
            days = time_since_join.days
            if days > 7:
                await remove_role(member, config.roles['newbie'])


async def full_check_member(bot: commands.Bot, member: discord.Member) -> None:
    await availability_check(bot, member)
    await voice_check(bot, member)

    for role in config.roles['role_check']:
        await add_role(member, role)

    await check_role_category(member, 'badges')
    await check_role_category(member, 'misc')
    await enforce_person_inactive_exclusivity(member)
    await check_member_join_date(bot, member)


async def check_all_members(bot: commands.Bot) -> None:
    server = bot.get_guild(config.TARGET_GUILD)
    await server.chunk()
    await general.update_status_checking(bot, '💠', 0)
    total_members = server.member_count
    member_n = 0
    members = server.members
    for member in members:
        member_n += 1
        percent = round(member_n * 100 / total_members, 1)
        if not member.bot:
            await full_check_member(bot, member)
        await general.update_status_checking(bot, '💠', percent)
    await general.update_status(bot, status=discord.Status.online)


async def check_inactivity(bot):
    chat_channel = bot.get_channel(config.channels['chat'])
    guild = bot.get_guild(config.TARGET_GUILD)
    await general.update_status_checking(bot, '🛌', 0.0)

    members_data = {
        m: {'last_message': None, 'last_bot_mention': None}
        for m in guild.members
        if not m.bot
    }

    checked_msg = 0
    async for msg in chat_channel.history(limit=30000):
        checked_msg += 1

        if checked_msg % 1750 == 0:
            await general.update_status_checking(bot, '🛌', round(checked_msg / 30000 * 100, 1))

        for member, data in members_data.items():
            if not data['last_message'] and msg.author == member:
                data['last_message'] = msg
            if (
                    not data['last_bot_mention']
                    and msg.author == bot.user
                    and member.display_name in msg.content
            ):
                data['last_bot_mention'] = msg

        if all(v['last_message'] and v['last_bot_mention'] for v in members_data.values()):
            break

    await general.update_status_checking(bot, '🛌', 100)

    now = discord.utils.utcnow()
    six_days_ago = now.timestamp() - 6 * 24 * 60 * 60

    m: discord.Member
    d: dict
    for m, d in members_data.items():
        if has_role(m, config.roles['inactive']):
            continue

        if has_role(m, config.roles['explained_inactive']):
            await add_role(m, config.roles['inactive'])
            await remove_role(m, config.roles['person'])
            continue


        last_msg_ts = (
            d['last_message'].created_at.timestamp() if d['last_message'] else None
        )
        last_mention_ts = (
            d['last_bot_mention'].created_at.timestamp()
            if d['last_bot_mention']
            else None
        )

        if (
                not last_msg_ts
                and not last_mention_ts
        ) or (
                (last_msg_ts and last_msg_ts < six_days_ago)
                and (last_mention_ts and last_mention_ts < six_days_ago)
        ):
            await add_role(m, config.roles['inactive'])
            await remove_role(m, config.roles['person'])

    await general.update_status(bot, status=discord.Status.online)


async def check_availability(bot):
    chat_channel = bot.get_channel(config.channels['chat'])
    guild = bot.get_guild(config.TARGET_GUILD)
    await general.update_status_checking(bot, '🔵', 0.0)

    members_data = {
        m: {'last_message': None, 'last_bot_mention': None}
        for m in guild.members
        if not m.bot
    }

    checked_msg = 0
    async for msg in chat_channel.history(limit=1250):
        checked_msg += 1

        if checked_msg % 208 == 0:
            await general.update_status_checking(bot, '🔵', round(checked_msg / 1250 * 100, 1))

        for member, data in members_data.items():
            if not data['last_message'] and msg.author == member:
                data['last_message'] = msg
            if (
                    not data['last_bot_mention']
                    and msg.author == bot.user
                    and member.display_name in msg.content
            ):
                data['last_bot_mention'] = msg

        if all(v['last_message'] and v['last_bot_mention'] for v in members_data.values()):
            break

    await general.update_status_checking(bot, '🔵', 100)

    now = discord.utils.utcnow()
    two_hours_ago = now.timestamp() - 2 * 60 * 60
    availability_role = bot.get_guild(config.TARGET_GUILD).get_role(config.roles['available'])

    m: discord.Member
    d: dict
    for m, d in members_data.items():
        if availability_role not in m.roles:
            continue

        if m.voice and m.voice.channel:
            continue

        last_msg_ts = (
            d['last_message'].created_at.timestamp() if d['last_message'] else None
        )
        last_mention_ts = (
            d['last_bot_mention'].created_at.timestamp()
            if d['last_bot_mention']
            else None
        )

        if (
                not last_msg_ts
                and not last_mention_ts
        ) or (
                (last_msg_ts and last_msg_ts < two_hours_ago)
                and (last_mention_ts and last_mention_ts < two_hours_ago)
        ):
            channel = bot.get_channel(config.channels['availability'])
            msg = await channel.fetch_message(config.channels['availability_message'])

            await remove_role(m, config.roles['availability'])
            await msg.remove_reaction(
                discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), m)
            await general.send(bot, config.message('unavailable_auto_bot', name=m.mention,
                                                   available_count=f"{general.emojify(str(await count_available(bot)), 'b')}"))

    await general.update_status(bot, status=discord.Status.online)