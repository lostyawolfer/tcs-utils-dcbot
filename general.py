import discord
import config
from discord.ext import commands

async def send(bot: commands.Bot, msg: str, where: str = 'chat') -> None:
    channel = bot.get_channel(config.channels[where])
    if channel:
        await channel.send(msg)
    await update_status(bot)



async def count_available(bot: commands.Bot) -> int:
    channel = bot.get_channel(config.channels['availability'])
    try:
        msg = await channel.fetch_message(config.channels['availability_message'])
    except discord.NotFound | discord.Forbidden:
        return 0
    found_reaction = None
    for reaction in msg.reactions:
        if reaction.emoji.id == config.channels['availability_reaction']:
            found_reaction = reaction
            break
    res = 0
    if found_reaction:
        res = found_reaction.count
    return res

async def count_in_vc(bot: commands.Bot, vc: str = 'vc') -> int:
    return len(bot.get_channel(config.channels[vc]).members)



async def set_status(bot: commands.Bot, status: str) -> None:
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))

async def update_status(bot: commands.Bot) -> None:
    vc_count = await count_in_vc(bot, 'vc')
    vc_2_count = await count_in_vc(bot, 'vc2')
    available_count = await count_available(bot)
    if not vc_count and not vc_2_count:
        await set_status(bot, f'{available_count} available')
    elif vc_count and not vc_2_count:
        await set_status(bot, f'{available_count} available / {vc_count} in vc 🟢')
    elif not vc_count and vc_2_count:
        await set_status(bot, f'{available_count} available / {vc_2_count} in vc 🟣')
    else:
        await set_status(bot, f'{available_count} available / vc - {vc_count} 🟢 - {vc_2_count} 🟣')



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


def subscript(text: str) -> str:
    conversion_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '/': '⸝', '(': '₍', ')': '₎'
    }
    converted_text = []
    for char in text:
        converted_text.append(conversion_map.get(char, char))
    return "".join(converted_text)




import functools

def has_perms(required_perm):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, member: discord.Member, *args, **kwargs):
            if member == ctx.author:
                return await ctx.send(config.message("nuh_uh"))
            if member == ctx.guild.me:
                return await ctx.send(config.message("nuh_uh"))
            if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
                return await ctx.send(config.message("nuh_uh"))
            author_perms = ctx.author.guild_permissions
            if not getattr(author_perms, required_perm, False):
                return await ctx.send(config.message("nuh_uh"))
            return await func(ctx, member, *args, **kwargs)
        return wrapper
    return decorator

def try_perm(func):
    @functools.wraps(func)
    async def wrapper(ctx, member: discord.Member, *args, **kwargs):
        try:
            await func(ctx, member, *args, **kwargs)
        except discord.Forbidden:
            await ctx.send(config.message("bot_doesnt_have_perms"))
            print(f"bot lacks permissions to moderate {member.display_name} (id {member.id})")
        except Exception as e:
            await ctx.send(config.message("bot_doesnt_have_perms"))
            print(f"error moderating {member.display_name} (id: {member.id}): {e}")
    return wrapper