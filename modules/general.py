import discord
import datetime
from discord.ext import commands
from modules import config


async def send(bot: commands.Bot, msg: str, where: str = 'chat') -> discord.Message:
    channel = bot.get_channel(config.channels[where])
    if channel:
        msg = await channel.send(msg)
    await update_status(bot)
    return msg


async def count_available(bot: commands.Bot) -> int:
    channel = bot.get_channel(config.channels['availability'])
    try:
        msg = await channel.fetch_message(config.channels['availability_message'])
    except (discord.NotFound, discord.Forbidden):
        return 0
    found_reaction: discord.Reaction | None = None
    for reaction in msg.reactions:
        if reaction.emoji.id == config.channels['availability_reaction']:
            found_reaction = reaction
            break
    res = 0
    if found_reaction:
        res = found_reaction.count
    if found_reaction and found_reaction.me:
        res -= 1
    return res

async def count_in_vc(bot: commands.Bot, vc: str = 'vc') -> int:
    return len(bot.get_channel(config.channels[vc]).members)

async def set_status(bot: commands.Bot, text: str, *, status: discord.Status = None) -> None:
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text), status=status)

async def update_status(bot: commands.Bot, status: discord.Status = None) -> None:
    time = f'{datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M")}'
    vc_count = await count_in_vc(bot, 'vc')
    vc_2_count = await count_in_vc(bot, 'vc2')
    available_count = await count_available(bot)
    if not vc_count and not vc_2_count:
        await set_status(bot, f'{available_count} available', status=status) # [{time}]
    elif vc_count and not vc_2_count:
        await set_status(bot, f'{available_count} available / {vc_count} in vc 🟢', status=status) # [{time}]
    elif not vc_count and vc_2_count:
        await set_status(bot, f'{available_count} available / {vc_2_count} in vc 🟣', status=status) # [{time}]
    else:
        await set_status(bot, f'{available_count} available / vc - {vc_count} 🟢 - {vc_2_count} 🟣', status=status) # [{time}]

async def update_status_checking(bot: commands.Bot, percent: float) -> None:
    time = f'{datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M")}'
    vc_count = await count_in_vc(bot, 'vc')
    vc_2_count = await count_in_vc(bot, 'vc2')
    available_count = await count_available(bot)
    if not vc_count and not vc_2_count:
        await set_status(bot, f'{percent}% / {available_count} available', status=discord.Status('idle')) # [{time}]
    elif vc_count and not vc_2_count:
        await set_status(bot, f'{percent}% / {available_count} available / {vc_count} in vc 🟢', status=discord.Status('idle')) # [{time}]
    elif not vc_count and vc_2_count:
        await set_status(bot, f'{percent}% / {available_count} available / {vc_2_count} in vc 🟣', status=discord.Status('idle')) # [{time}]
    else:
        await set_status(bot, f'{percent}% / {available_count} available / vc - {vc_count} 🟢 - {vc_2_count} 🟣', status=discord.Status('idle')) # [{time}]



def has_role(member: discord.Member, role_id: int) -> bool:
    role = member.guild.get_role(role_id)
    if not role or role not in member.roles:
        return False
    return True

def has_role_object(member: discord.Member, role: discord.Role) -> bool:
    if not role or role not in member.roles:
        return False
    return True



async def add_role(member: discord.Member, role_id: int) -> None:
    role = member.guild.get_role(role_id)
    if not has_role_object(member, role):
        await member.add_roles(role)

async def remove_role(member: discord.Member, role_id: int) -> None:
    role = member.guild.get_role(role_id)
    if has_role_object(member, role):
        await member.remove_roles(role)


def emojify(text: str, color: str = '') -> str:
    converted_text = ''
    for char in text:
        converted_text += config.emoji[f'{char}{color}']
    return "".join(converted_text)




import functools

def work_in_progress(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        return await ctx.send(config.message("wip"))
    return wrapper

def has_perms(required_perm: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if required_perm == 'owner':
                if ctx.author.id != ctx.guild.owner_id:
                    return await ctx.send(config.message("nuh_uh"))

            else:
                author_perms = ctx.author.guild_permissions
                if not getattr(author_perms, required_perm, False):
                    return await ctx.send(config.message("nuh_uh"))

            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def can_moderate_member(func):
    @functools.wraps(func)
    async def wrapper(ctx, member: discord.Member = None, *args, **kwargs):
        if not member:
            await ctx.send(config.message("bot_doesnt_have_perms"))
            return await ctx.send('<@534097411048603648> fix ur fucking bot\n'
                                  'you added a @can_moderate_member decorator where you shouldn\'t have dumbass\n'
                                  '-# [can_moderate_member expects a member in the command args, no member arg found]')
        if member == ctx.author:
            return await ctx.send(config.message("nuh_uh"))
        if member == ctx.guild.me:
            return await ctx.send(config.message("nuh_uh"))
        if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(config.message("nuh_uh"))
        return await func(ctx, member, *args, **kwargs)
    return wrapper

def try_bot_perms(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except discord.Forbidden as e:
            await ctx.send(config.message("bot_doesnt_have_perms"))
            return await ctx.send(f'<@534097411048603648> fix ur fucking bot\n```{e}```')
        except Exception as e:
            await ctx.send(config.message("bot_doesnt_have_perms"))
            print(f"error in try_perm: {e}")
            return await ctx.send(f'<@534097411048603648> fix ur fucking bot\n```{e}```')
    return wrapper