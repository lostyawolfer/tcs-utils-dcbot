import asyncio
import discord
from discord.ext import commands
from modules import config


async def send(bot: commands.Bot, msg: str, where: str = 'chat') -> discord.Message:
    channel = bot.get_channel(config.channels[where])
    if channel:
        msg = await channel.send(msg)
    await update_status(bot)
    return msg

async def timed_delete_msg(msg: discord.Message, text: str, duration: int = 10):
    for i in range(1, duration):
        if i <= 11:
            await msg.edit(content=f':clock{duration-i}: {text}')
            await asyncio.sleep(1)
        else:
            await msg.edit(content=f':white_check_mark: {text}')
            await asyncio.sleep(1)
    await msg.delete()

async def send_timed_delete_msg(bot: commands.Bot, text: str, duration: int = 10, where: str = 'chat') -> None:
    msg = await send(bot, text, where=where)
    for i in range(1, duration):
        if i <= 11:
            await msg.edit(content=f':clock{duration-i}: {text}')
            await asyncio.sleep(1)
        else:
            await msg.edit(content=f':white_check_mark: {text}')
            await asyncio.sleep(1)
    await msg.delete()



async def count_filtered_members(bot: commands.Bot) -> int:
    guild = bot.get_guild(config.TARGET_GUILD)
    excluded_role_id = 1427013313837011175 # alts
    excluded_role = guild.get_role(excluded_role_id)

    if excluded_role is None:
        print(f"warning: role id {excluded_role_id} not found")

    member_count = 0
    for member in guild.members:
        if member.bot:
            continue
        if excluded_role and excluded_role in member.roles:
            continue
        member_count += 1
    return member_count

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


async def get_status_text(bot: commands.Bot, short: bool = False) -> str:
    vc_count = await count_in_vc(bot, 'vc')
    vc_2_count = await count_in_vc(bot, 'vc2')
    vc_3_count = await count_in_vc(bot, 'vc3')
    available_count = await count_available(bot)
    members = await count_filtered_members(bot)

    text_members = f'{members} 👥'

    text_in_vc = ''
    if vc_count or vc_2_count or vc_3_count:
        text_in_vc = ' / vc'
        if vc_count:
            text_in_vc += f' - {vc_count} 🟢'
        if vc_2_count:
            text_in_vc += f' - {vc_2_count} 🟣'
        if vc_3_count:
            text_in_vc += f' - {vc_3_count} 🔴'

    text_available = ''
    if available_count:
        text_available = f' / {available_count} available'
        if vc_count or vc_2_count or vc_3_count:
            text_available = f' / {available_count} av.'

    status = f'{text_members}{text_available}{text_in_vc}'

    return status


async def update_status(bot: commands.Bot, status: discord.Status = None) -> None:
    status_text = await get_status_text(bot)
    await set_status(bot, status_text, status=status)

async def update_status_checking(bot: commands.Bot, check_type: str, percent: float) -> None:
    status_text = await get_status_text(bot, True)
    status_text = f'{check_type} {percent}% // {status_text}'
    await set_status(bot, status_text, status=discord.Status('idle'))


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




async def get_replied_message(ctx):
    ref = ctx.message.reference
    if not ref or not ref.message_id:
        return None  # not a reply

    msg = ref.resolved  # may already be cached and ready
    if isinstance(msg, discord.Message):
        return msg

    # fallback: fetch from the API
    try:
        return await ctx.channel.fetch_message(ref.message_id)
    except discord.NotFound:
        return None
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        return None

def inject_reply(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        if not args and ctx.message.reference:
            ref = ctx.message.reference
            msg = ref.resolved

            if not isinstance(msg, discord.Message):
                try:
                    msg = await ctx.channel.fetch_message(ref.message_id)
                except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                    msg = None

            if msg and isinstance(msg.author, discord.Member):
                return await func(ctx, msg.author, *args, **kwargs)

        return await func(ctx, *args, **kwargs)

    return wrapper