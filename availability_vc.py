import discord
from discord.ext import commands
import config
import general
from general import has_role, send, add_role, remove_role, count_available, count_in_vc, emojify


async def voice_check(bot: commands.Bot, member: discord.Member) -> None:
    async def check(vc: str, role: str, leader_role: str, reverse_role: str, join_msg_id: str, leave_msg_id: str):
        channel = member.guild.get_channel(config.channels[vc])
        members = await count_in_vc(bot, vc)
        if member.voice and member.voice.channel == channel:
            if not has_role(member, config.roles[role]):
                await send(bot, config.message(join_msg_id, name=member.display_name, count=f'{emojify(f'({members})')}'))
            if has_role(member, config.roles['leader']):
                await add_role(member, config.roles[leader_role])
            await add_role(member, config.roles[role])
            await remove_role(member, config.roles[reverse_role])
        else:
            if has_role(member, config.roles[role]):
                await send(bot, config.message(leave_msg_id, name=member.display_name, count=f'{emojify(f'({members})')}'))
            await remove_role(member, config.roles[role])
            await remove_role(member, config.roles[leader_role])
            await add_role(member, config.roles[reverse_role])

    await check('vc', 'in_vc', 'in_vc_leader', 'not_in_vc', 'join_vc', 'leave_vc')
    await check('vc2', 'in_vc_2', 'in_vc_2_leader', 'not_in_vc_2', 'join_vc_2', 'leave_vc_2')



async def add_availability(bot: commands.Bot, member: discord.Member) -> None:
    available_people = await count_available(bot)
    if not has_role(member, config.roles['available']):
        if available_people >= 8:
            await send(bot, config.message('available_ping', name=member.display_name, available_count=f'{emojify(f'({available_people})')}'))
        else:
            await send(bot, config.message('available', name=member.display_name, available_count=f'{emojify(f'({available_people})')}'))

    if has_role(member, config.roles['leader']):
        await add_role(member, config.roles['available_leader'])
    await add_role(member, config.roles['available'])
    await remove_role(member, config.roles['not_available'])



    msg = await member.guild.get_channel(config.channels['availability']).fetch_message(config.channels['availability_message'])
    await msg.remove_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), member.guild.me)

async def remove_availability(bot: commands.Bot, member: discord.Member) -> None:
    available_people = await count_available(bot)
    if has_role(member, config.roles['available']):
        if available_people >= 8:
            await send(bot, config.message('unavailable_ping', name=member.display_name, available_count=f'{emojify(f'({available_people})')}'))
        else:
            await send(bot, config.message('unavailable', name=member.display_name, available_count=f'{emojify(f'({available_people})')}'))

    await remove_role(member, config.roles['available'])
    await remove_role(member, config.roles['available_leader'])
    await add_role(member, config.roles['not_available'])


    if available_people == 0:
        msg = await member.guild.get_channel(config.channels['availability']).fetch_message(config.channels['availability_message'])
        await msg.add_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'))


async def pure_availability_check(bot: commands.Bot, member: discord.Member) -> None:
    channel = member.guild.get_channel(config.channels['availability'])
    try:
        msg = await channel.fetch_message(config.channels['availability_message'])
    except discord.NotFound | discord.Forbidden:
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

