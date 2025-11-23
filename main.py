import datetime

import discord
from discord.ext import commands
from config import message, check_guild, TARGET_GUILD, ROLES, CHANNELS, TOKEN

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

async def send(msg: str) -> None:
    guild = bot.get_guild(TARGET_GUILD)
    channel = guild.get_channel(CHANNELS['chat'])
    if channel:
        await channel.send(msg)



def has_role(member: discord.Member, role_id: int) -> bool:
    guild = member.guild
    if not check_guild(guild.id):
        return False

    role = guild.get_role(role_id)
    if not role:
        return False

    if role in member.roles:
        return True
    return False

async def add_role(member: discord.Member, role_id: int) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    if not has_role(member, role_id):
        role = guild.get_role(role_id)
        await member.add_roles(role)

async def remove_role(member: discord.Member, role_id: int) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    role = guild.get_role(role_id)
    if not role:
        return

    if has_role(member, role_id):
        role = guild.get_role(role_id)
        await member.remove_roles(role)



async def check_voice_state(member: discord.Member) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    vc = guild.get_channel(CHANNELS['vc'])
    if not vc:
        return

    if member.voice and member.voice.channel == vc:
        if not has_role(member, ROLES['in_vc']):
            await send(message('join_vc', name=member.display_name))

        if has_role(member, ROLES['leader']):
            await add_role(member, ROLES['in_vc_leader'])
        await add_role(member, ROLES['in_vc'])
        await remove_role(member, ROLES['not_in_vc'])

    else:
        if has_role(member, ROLES['in_vc']):
            await send(message('leave_vc', name=member.display_name))
        await remove_role(member, ROLES['in_vc'])
        await remove_role(member, ROLES['in_vc_leader'])
        await add_role(member, ROLES['not_in_vc'])


async def count_available_people() -> int:
    guild = bot.get_guild(TARGET_GUILD)
    channel = guild.get_channel(CHANNELS['availability'])
    try:
        msg = await channel.fetch_message(CHANNELS['availability_message'])
    except discord.NotFound | discord.Forbidden:
        return 0

    found_reaction = None
    for reaction in msg.reactions:
        if reaction.emoji.id == CHANNELS['availability_reaction']:
            found_reaction = reaction
            break

    res = 0
    if found_reaction:
        res = found_reaction.count
    return res

async def pure_check_availability_state(member: discord.Member) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    channel = guild.get_channel(CHANNELS['availability'])

    try:
        msg = await channel.fetch_message(CHANNELS['availability_message'])
    except discord.NotFound | discord.Forbidden:
        return

    found_reaction = None
    for reaction in msg.reactions:
        if reaction.emoji.id == CHANNELS['availability_reaction']:
            found_reaction = reaction
            break
    if found_reaction:
        async for user in found_reaction.users():
            if user == member:
                if not has_role(member, ROLES['available']):
                    await send(message('available', name=member.display_name, available_count=await count_available_people()))

                if has_role(member, ROLES['leader']):
                    await add_role(member, ROLES['available_leader'])
                await add_role(member, ROLES['available'])
                await remove_role(member, ROLES['not_available'])
                return

        if has_role(member, ROLES['available']):
            await send(message('unavailable', name=member.display_name, available_count=await count_available_people()))

        await remove_role(member, ROLES['available'])
        await remove_role(member, ROLES['available_leader'])
        await add_role(member, ROLES['not_available'])
    else:
        channel = bot.get_channel(CHANNELS['availability'])
        msg = await channel.fetch_message(CHANNELS['availability_message'])
        await msg.add_reaction(discord.PartialEmoji(id=CHANNELS['availability_reaction'], name='available'))


async def add_availability(member: discord.Member) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    available_people = await count_available_people()
    if not has_role(member, ROLES['available']):
        await send(message('available', name=member.display_name, available_count=available_people))
        if available_people >= 8:
            await send(message('available_ping'))

    if has_role(member, ROLES['leader']):
        await add_role(member, ROLES['available_leader'])
    await add_role(member, ROLES['available'])
    await remove_role(member, ROLES['not_available'])
    return

async def remove_availability(member: discord.Member) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    if has_role(member, ROLES['available']):
        await send(message('unavailable', name=member.display_name, available_count=await count_available_people()))

    await remove_role(member, ROLES['available'])
    await remove_role(member, ROLES['available_leader'])
    await add_role(member, ROLES['not_available'])





@bot.event
async def on_ready():
    for guild in bot.guilds:
        if check_guild(guild.id):
            status_message = await guild.get_channel(CHANNELS['chat']).send('bot restarted\n-# ...')
            await status_message.edit(content=f'bot restarted\n-# *preparing*')
            member_n = 0
            for member in guild.members:
                member_n += 1
                await status_message.edit(
                    content=f'bot restarted\n-# *checking member {member_n}/{guild.member_count}* …')
                await check_voice_state(member)
                await pure_check_availability_state(member)
                await status_message.edit(
                    content=f'bot restarted\n-# *checking member {member_n}/{guild.member_count}* ✓')
            await status_message.edit(content=f'bot restarted\n-# *done*')

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if not check_guild(guild.id):
        return

    vc = guild.get_channel(CHANNELS['vc'])
    if not vc:
        return

    await check_voice_state(member)

@bot.event
async def on_raw_reaction_add(payload):
    if not check_guild(payload.guild_id):
        return
    if payload.message_id == CHANNELS['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == CHANNELS['availability_reaction']:
            await add_availability(bot.get_guild(payload.guild_id).get_member(payload.user_id))


@bot.event
async def on_raw_reaction_remove(payload):
    if not check_guild(payload.guild_id):
        return
    if payload.message_id == CHANNELS['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == CHANNELS['availability_reaction']:
            await remove_availability(bot.get_guild(payload.guild_id).get_member(payload.user_id))

@bot.event
async def on_member_join(member):
    guild = member.guild
    if not check_guild(guild.id):
        return

    if member.bot:
        await send(message('join_bot', mention=member.mention))
        await add_role(member, ROLES['bot'])
    else:
        await send(message('join', mention=member.mention))
        await send('-# hey there! check out <#1426974985402187776> <#1432401559672848507> <#1434653852367585300>')
        for role in ROLES['new_people']:
            await add_role(member, role)

@bot.event
async def on_member_remove(member):
    guild = member.guild
    if not check_guild(guild.id):
        return

    if member.bot:
        await send(message('kick_bot', mention=member.mention))

    else:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await send(message('kick', mention=member.mention))
                    return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await send(message('ban', mention=member.mention))
                    return

        await send(message('leave', mention=member.mention))






@bot.command()
async def test(ctx):
    await ctx.send('test pass')

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:  # Prevent bot from kicking itself
        return await ctx.send(message("nuh_uh"))
    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        await ctx.send(message("nuh_uh"))
        print(f"Bot lacks permissions to kick {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("nuh_uh"))
        print(f"Error kicking {member.display_name} (ID: {member.id}): {e}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:  # Prevent bot from kicking itself
        return await ctx.send(message("nuh_uh"))
    try:
        await member.ban(reason=reason)
    except discord.Forbidden:
        await ctx.send(message("nuh_uh"))
        print(f"Bot lacks permissions to kick {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("nuh_uh"))
        print(f"Error kicking {member.display_name} (ID: {member.id}): {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:
        return await ctx.send(message("nuh_uh"))

    timeout_duration = None
    try:
        if duration.endswith('s'):
            seconds = int(duration[:-1])
            timeout_duration = datetime.timedelta(seconds=seconds)
        elif duration.endswith('m'):
            minutes = int(duration[:-1])
            timeout_duration = datetime.timedelta(minutes=minutes)
        elif duration.endswith('h'):
            hours = int(duration[:-1])
            timeout_duration = datetime.timedelta(hours=hours)
        elif duration.endswith('d'):
            days = int(duration[:-1])
            timeout_duration = datetime.timedelta(days=days)
        elif duration.endswith('w'):
            weeks = int(duration[:-1])
            timeout_duration = datetime.timedelta(weeks=weeks)
        else:
            return await ctx.send("wrong duration format you moron")

        if not timeout_duration: # Should be caught by the else above, but for safety
            return await ctx.send("wrong duration format you moron")

        if timeout_duration > datetime.timedelta(days=28):
            return await ctx.send("you can't mute for more than 28 days because discord is a moron sorry")

        await member.timeout(timeout_duration, reason=reason)
        await ctx.send(f"muted the guy :white_check_mark:")

    except ValueError:
        return await ctx.send("wrong duration format you moron")
    except discord.Forbidden:
        await ctx.send(message("nuh_uh"))
        print(f"Bot lacks permissions to timeout {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("nuh_uh"))
        print(f"Error muting {member.display_name} (ID: {member.id}): {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member, *, reason: str = None):
    if not member.is_timed_out():
        return await ctx.send(message("nuh_uh"))

    try:
        await member.timeout(None, reason=reason) # Setting duration to None removes timeout
        await ctx.send(f"unmuted :white_check_mark:")
        print(f"Unmuted {member.display_name} (ID: {member.id}) by {ctx.author.display_name} for: {reason}")
    except discord.Forbidden:
        await ctx.send(message("nuh_uh"))
        print(f"Bot lacks permissions to unmute {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("nuh_uh"))
        print(f"Error unmuting {member.display_name} (ID: {member.id}): {e}")



if __name__ == '__main__':
    bot.run(TOKEN)