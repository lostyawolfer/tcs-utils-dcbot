import asyncio

import discord
from discord.ext import commands
from modules import config, general
from modules.general import has_role, send, add_role, remove_role, count_available, count_in_vc, emojify, \
    timed_delete_msg


async def voice_check(bot: commands.Bot, member: discord.Member) -> None:
    async def check(vc: str, vc_role: str, vc_leader_role: str, reverse_role: str, join_msg_id: str, leave_msg_id: str, color: str = 'g'):
        channel = member.guild.get_channel(config.channels[vc])
        members = await count_in_vc(bot, vc)
        if member.voice and member.voice.channel == channel:
            if not has_role(member, config.roles[vc_role]):
                await send(bot, config.message(join_msg_id, name=member.display_name, count=f'{emojify(f'{members}', f'{color}')}'))
            if has_role(member, config.roles['leader']):
                await add_role(member, config.roles[vc_leader_role])
            await add_role(member, config.roles[vc_role])
            await remove_role(member, config.roles[reverse_role])
        else:
            if has_role(member, config.roles[vc_role]):
                await send(bot, config.message(leave_msg_id, name=member.display_name, count=f'{emojify(f'{members}', f'{color}')}'))
            await remove_role(member, config.roles[vc_role])
            await remove_role(member, config.roles[vc_leader_role])
            if has_role(member, config.roles['available']):
                await add_role(member, config.roles[reverse_role])

    await check('vc', 'in_vc', 'in_vc_leader', 'available_not_in_vc', 'join_vc', 'leave_vc')
    await check('vc2', 'in_vc_2', 'in_vc_2_leader', 'available_not_in_vc_2', 'join_vc_2', 'leave_vc_2', 'p')





async def add_availability(bot: commands.Bot, member: discord.Member) -> None:
    if not has_role(member, config.roles['available']):
        available_people = await count_available(bot)
        if available_people >= 8:
            await send(bot, config.message('available_ping', name=member.display_name, available_count=f'{emojify(f'{available_people}', 'b')}'))
        else:
            await send(bot, config.message('available', name=member.display_name, available_count=f'{emojify(f'{available_people}', 'b')}'))

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

    await add_role(member, config.roles['available'])
    await remove_role(member, config.roles['not_available'])

    msg = await member.guild.get_channel(config.channels['availability']).fetch_message(
        config.channels['availability_message'])
    await msg.remove_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), member.guild.me)


async def remove_availability(bot: commands.Bot, member: discord.Member) -> None:
    available_people = await count_available(bot)
    if has_role(member, config.roles['available']):
        if available_people >= 8:
            await send(bot, config.message('unavailable_ping', name=member.display_name, available_count=f'{emojify(f'{available_people}', 'b')}'))
        else:
            await send(bot, config.message('unavailable', name=member.display_name, available_count=f'{emojify(f'{available_people}', 'b')}'))

    await remove_role(member, config.roles['available'])
    await remove_role(member, config.roles['available_leader'])
    await add_role(member, config.roles['not_available'])
    await remove_role(member, config.roles['available_not_in_vc'])
    await remove_role(member, config.roles['available_not_in_vc_2'])

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

    await check_member_join_date(bot, member)




async def check_all_members(bot: commands.Bot) -> None:
    #msg = await general.send(bot, ':busts_in_silhouette: checking members...')
    server = bot.get_guild(config.TARGET_GUILD)
    await server.chunk()
    await general.update_status_checking(bot, 0)
    total_members = server.member_count
    member_n = 0
    members = server.members
    for member in members:
        member_n += 1
        percent = round(member_n * 100 / total_members, 1)
        if not member.bot:
            await full_check_member(bot, member)
        await general.update_status_checking(bot, '💠', percent)
    await general.update_status(bot, status=discord.Status('online'))
    #await timed_delete_msg(msg, 'members checked successfully', 10)
