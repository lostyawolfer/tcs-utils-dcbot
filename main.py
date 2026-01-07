import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from modules import config, activity, moderation, general
from modules.activity import check_availability
from modules.general import timed_delete_msg, send_timed_delete_msg, add_role, remove_role, has_role
from modules.saves import create_save, disband_save, rename_save
from modules.points import calculate_points, get_ranked_leaderboard, update_leaderboard_message, parse_challenge_role


################################################################

version = 'v3.1.4'

changelog = \
    f"""
:tada: **{version} changelog**
- idk i didnt come up with a changelog
"""

################################################################


intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)

# Spoiler season tracking
SPOILER_STATE_FILE = 'spoiler_state.json'
spoiler_state = {
    'active': False,
    'until': None,
    'emoji': None,
    'event_name': None,
    'access_message_id': None
}


def load_spoiler_state():
    global spoiler_state
    if os.path.exists(SPOILER_STATE_FILE):
        with open(SPOILER_STATE_FILE, 'r') as f:
            spoiler_state = json.load(f)


def save_spoiler_state():
    with open(SPOILER_STATE_FILE, 'w') as f:
        json.dump(spoiler_state, f)


@tasks.loop(minutes=5)
async def check_spoiler_season():
    if spoiler_state['active'] and spoiler_state['until']:
        until_dt = datetime.fromisoformat(spoiler_state['until']) # type: ignore
        if datetime.now(timezone.utc) >= until_dt:
            await end_spoiler_season()


async def end_spoiler_season():
    guild = bot.get_guild(config.TARGET_GUILD)
    spoiler_role = guild.get_role(config.channels['spoiler_role'])
    spoiler_channel = guild.get_channel(config.channels['spoiler'])
    access_channel = guild.get_channel(config.channels['spoiler_access'])

    # Remove reactions if message exists
    if spoiler_state['access_message_id']:
        try:
            msg = await access_channel.fetch_message(spoiler_state['access_message_id'])
            await msg.clear_reactions()
        except Exception as e:
            pass

    # Hide access channel
    await access_channel.set_permissions(guild.default_role, view_channel=False)

    # Send message in spoilers channel
    await spoiler_channel.send('# spoiler window ended!')

    # Update state
    spoiler_state['active'] = False
    spoiler_state['until'] = None
    spoiler_state['emoji'] = None
    spoiler_state['event_name'] = None
    spoiler_state['access_message_id'] = None
    save_spoiler_state()


@tasks.loop(hours=6)
async def member_checker():
    await activity.check_all_members(bot)
    await activity.check_inactivity(bot)

@tasks.loop(hours=1)
async def availability_checker():
    await asyncio.sleep(600)
    await check_availability(bot)


@bot.event
async def on_ready():
    load_spoiler_state()
    await general.send(bot, f':radio_button: bot connected... {version}')
    await general.set_status(bot, 'starting up...', status=discord.Status.idle) # type: ignore
    await bot.wait_until_ready()
    await general.send(bot, f':ballot_box_with_check: restart complete!')
    await general.send(bot, changelog)

@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def start_checking(ctx):
    """Manually start the member checking loop."""
    if member_checker.is_running():
        return await ctx.send("member checking is already running")
    member_checker.start()
    check_spoiler_season.start()
    availability_checker.start()
    return await ctx.send("started member checking loop :white_check_mark:")

@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def stop_checking(ctx):
    """Stop the member checking loop."""
    if not member_checker.is_running():
        return await ctx.send("member checking is not running")
    member_checker.cancel()
    check_spoiler_season.cancel()
    availability_checker.cancel()
    await general.update_status(bot, status=discord.Status.online)
    return await ctx.send("stopped member checking loop :white_check_mark:")

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def check_members(ctx):
    await activity.check_all_members(bot)

@bot.command()
@general.try_bot_perms
#@general.inject_reply
@general.has_perms('manage_roles')
async def check(ctx, member: discord.Member = None):
    await activity.full_check_member(bot, member)
    await send_timed_delete_msg(bot, f'checked {member.display_name}')

@bot.command()
@general.try_bot_perms
async def test(ctx):
    await ctx.send(f'test pass\n-# {version}')


@bot.event
async def on_voice_state_update(member, before, after):
    if not config.check_guild(member.guild.id) or (member and member.bot):
        return
    await activity.voice_check(bot, member)




# Reaction Roles - easy hot-swap
REACTION_ROLES = {
    1451676590558937221: {  # message_id
        "⚠️": 1451675068114669740,  # emoji: role_id
    }
}

@bot.event
async def on_raw_reaction_add(payload):
    member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
    if not config.check_guild(payload.guild_id) or (member and member.bot):
        return

    if payload.message_id == config.channels['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == config.channels['availability_reaction']:
            await activity.add_availability(bot, bot.get_guild(payload.guild_id).get_member(payload.user_id))

    # Reaction roles
    if payload.message_id in REACTION_ROLES:
        emoji_str = str(payload.emoji)
        if emoji_str in REACTION_ROLES[payload.message_id]:
            role_id = REACTION_ROLES[payload.message_id][emoji_str]
            await general.add_role(member, role_id)

@bot.event
async def on_raw_reaction_remove(payload):
    member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
    if not config.check_guild(payload.guild_id) or (member and member.bot):
        return

    if payload.message_id == config.channels['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == config.channels['availability_reaction']:
            await activity.remove_availability(bot, bot.get_guild(payload.guild_id).get_member(payload.user_id))

    # Reaction roles
    if payload.message_id in REACTION_ROLES:
        emoji_str = str(payload.emoji)
        if emoji_str in REACTION_ROLES[payload.message_id]:
            role_id = REACTION_ROLES[payload.message_id][emoji_str]
            await general.remove_role(member, role_id)


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles

        # Handle person/inactive/explained inactive exclusivity
        for role in added_roles:
            if role.id == config.roles['person']:
                await remove_role(after, config.roles['inactive'])
            if role.id in [config.roles['inactive'], config.roles['explained_inactive']]:
                await remove_role(after, config.roles['person'])

        for role in removed_roles:
            if role.id == config.roles['person']:
                if not has_role(after, config.roles['inactive']) and not has_role(after,
                                                                                  config.roles['explained_inactive']):
                    await add_role(after, config.roles['inactive'])
            if role.id == config.roles['inactive']:
                if not has_role(after, config.roles['explained_inactive']) and not has_role(after,
                                                                                            config.roles['person']):
                    await add_role(after, config.roles['person'])

        # Challenge role changes
        for role in added_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                emoji_map = {
                    '🟢': '<:yes:1454978155222663278>',
                    '⭐': '<:star_completion:1453452694592159925>',
                    '☄️': '<:star_pure_completion:1453452636618752214>'
                }
                emoji = emoji_map.get(role_info['tier_emoji'], '<:yes:1454978155222663278>')
                await general.send(bot,
                                   f'{emoji} {after.mention} completed **{role_info["name"]}** ({role_info["points"]} pts)')
                await update_leaderboard_message(bot, after.guild)

        for role in removed_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                await general.send(bot,
                                   f'<:no:1454950318042255410> {after.mention}\'s **{role_info["name"]}** completion was taken')
                await update_leaderboard_message(bot, after.guild)

        # Existing role update logic
        for role in added_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('promotion', mention=after.mention))
                await general.send(bot, config.message('promotion_welcome', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('new_leader', mention=after.mention))
            if role.id == config.roles['inactive']:
                await general.send(bot, config.message('inactive', mention=after.mention))
            if role.id == config.roles['explained_inactive']:
                await general.send(bot, config.message('explained_inactive', mention=after.mention))
            if role.id == config.roles['spoiler']:
                await general.send(bot, config.message('spoiler_add', mention=after.mention), 'spoiler')
            if role.id in config.roles['category:badges']['other']:
                await general.remove_role(after, config.roles['category:badges']['none'])
            if role.id in config.roles['category:misc']['other']:
                await general.remove_role(after, config.roles['category:misc']['none'])

        for role in removed_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('demotion', mention=after.mention))
                await general.send(bot, config.message('demotion_goodbye', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('leader_removed', mention=after.mention))
            if role.id == config.roles['newbie']:
                await general.send(bot, config.message('newbie', mention=after.mention))
            if role.id == config.roles['inactive']:
                await general.send(bot, config.message('inactive_revoke', mention=after.mention))
            if role.id == config.roles['spoiler']:
                await general.send(bot, config.message('spoiler_remove', mention=after.mention), 'spoiler')

        if any(role.id in config.roles['category:badges']['other'] for role in removed_roles):
            await activity.check_role_category(after, 'badges')
        if any(role.id in config.roles['category:misc']['other'] for role in removed_roles):
            await activity.check_role_category(after, 'misc')

    if before.nick != after.nick:
        old = before.nick if before.nick else before.display_name
        new = after.nick if after.nick else after.display_name
        await general.send(bot, config.message('name_change', mention=after.mention, old_name=old, new_name=new))

@bot.event
async def on_member_join(member):
    guild = member.guild
    if not config.check_guild(guild.id):
        return

    if member.bot:
        await general.send(bot, config.message('join_bot', mention=member.mention))
        await general.add_role(member, config.roles['bot'])
    else:
        await general.send(bot, config.message('join', mention=member.mention))
        await general.send(bot, msg='-# read below for just a quick tour around :3\n'
                                    '-# channels you really should check out: <#1442604555798974485> <#1426974985402187776> <#1432401559672848507>\n'
                                    '-# grab <#1434653852367585300> when you are ready to play! (don\'t forget to remove it when you stop being available!)\n'
                                    '-# join <#1426974154556702720> at any time!\n'
                                    '-# please respect others and remain active! unexplained long inactivity is something very frowned upon here')
        await general.send(bot, f':new: <@&{config.roles['mod']}> hey, we got a new member in the server! nice work! a friendly reminder to set their nickname to their roblox display name :3', 'mod_chat')
        for role in config.roles['new_people']:
            await general.add_role(member, role)


@bot.event
async def on_member_remove(member):
    guild = member.guild
    if not config.check_guild(guild.id):
        return

    if member.bot:
        await general.send(bot, config.message('kick_bot', mention=member.mention))

    else:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await general.send(bot, config.message('kick', mention=member.mention))
                    return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await general.send(bot, config.message('ban', mention=member.mention))
                    return

        await general.send(bot, config.message('leave', mention=member.mention))


import re


async def log_message(bot: commands.Bot, message: discord.Message):
    if message.channel.id == config.channels['logs_channel']:
        return

    print(f'#{message.channel.name} | @{message.author.display_name} >> {message.content}')

    channel = bot.get_channel(config.channels['logs_channel'])
    timestamp = f"<t:{int(message.created_at.timestamp())}:f>"
    content = message.content

    if not content.strip() and not message.attachments and not message.stickers:
        content = "*[no visible content]*"

    log_message = (
        f'### {message.channel.mention} >> {message.author.mention} — {timestamp}\n'
        f'{content}\n'
    )

    attachment_urls = [attachment.url for attachment in message.attachments]
    if attachment_urls:
        log_message += "\n" + "\n".join(attachment_urls)

    await channel.send(log_message, allowed_mentions=discord.AllowedMentions.none(), silent=True,
                       stickers=message.stickers)

@bot.event
async def on_message(message: discord.Message):
    await log_message(bot, message)
    if message.author == bot.user:
        return

    # ps link
    if '<#1426974154556702720>' in message.content or 'ps' in re.findall(r"\b\w+\b", message.content.lower()):
        await message.channel.send(
            f'link: **https://www.roblox.com/share?code=1141897d2bd9a14e955091d8a4061ee5&type=Server**',
            suppress_embeds=True)

    # slur check
    if 'nigga' in message.content.lower() or 'nigger' in message.content.lower():
        await message.channel.send(
            f'[[<@534097411048603648>]] i will personally fix ur fucking skin color if you say that word again')

    # roleplay actions
    rp_actions = {
        'kill': 'rp_kill',
        'hug': 'rp_hug',
        'kiss': 'rp_kiss',
        'high five': 'rp_high_five',
        'highfive': 'rp_high_five',
        'shake hands': 'rp_handshake',
        'handshake': 'rp_handshake',
        'burn': 'rp_burn',
        'punch': 'rp_punch',
        'slap': 'rp_slap',
        'pat': 'rp_pat',
        'touch': 'rp_touch',
    }

    content_lower = message.content.lower().strip()
    target = None
    action = None

    # check if replying with just the action word
    if message.reference and message.reference.resolved:
        replied_msg = message.reference.resolved
        if isinstance(replied_msg.author, discord.Member):
            for action_word, action_key in rp_actions.items():
                if content_lower == action_word:
                    action = action_key
                    target = replied_msg.author
                    break

    # check for "action @member" pattern
    if not action:
        for action_word, action_key in rp_actions.items():
            pattern = rf'^{re.escape(action_word)}\s+<@!?(\d+)>$'
            match = re.match(pattern, content_lower)
            if match:
                member_id = int(match.group(1))
                member = message.guild.get_member(member_id)
                if member:
                    action = action_key
                    target = member
                    break

    if action and target:
        response = config.message(action, author=message.author.mention, target=target.mention)
        await message.channel.send(response)

    await bot.process_commands(message)


@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def spoiler(ctx, action: str = None, *args):
    if not action:
        return await ctx.send(
            'usage: `.spoiler start <emoji> <event-name> [until-timestamp]` / `.spoiler cancel` / `.spoiler rename <emoji> <new_name>`')

    guild = ctx.guild
    spoiler_channel = guild.get_channel(config.channels['spoiler'])
    access_channel = guild.get_channel(config.channels['spoiler_access'])
    chat_channel = guild.get_channel(config.channels['chat'])

    if action == 'start':
        if spoiler_state['active']:
            return await ctx.send('spoiler season is already active')

        if len(args) < 2:
            return await ctx.send('usage: `.spoiler start <emoji> <event-name> [until-timestamp]`')

        emoji = args[0]
        event_name = args[1]

        # Calculate until timestamp
        if len(args) >= 3:
            try:
                until_ts = int(args[2])
                until_dt = datetime.fromtimestamp(until_ts, tz=timezone.utc)
            except:
                return await ctx.send('invalid timestamp')
        else:
            until_dt = datetime.now(timezone.utc) + timedelta(hours=48)
            until_dt = until_dt.replace(minute=0, second=0, microsecond=0)

        # Make access channel visible
        await access_channel.set_permissions(guild.default_role, view_channel=True)

        # Rename spoiler channel
        new_channel_name = f'{emoji}┃{event_name}-spoilers'
        await spoiler_channel.edit(name=new_channel_name)

        # Delete existing messages in access channel
        async for message in access_channel.history(limit=100):
            await message.delete()

        # Send access message
        until_unix = int(until_dt.timestamp())
        access_msg = await access_channel.send(
            f'# click the reaction below if you wish to gain access to `{spoiler_channel.name}` channel\n\n'
            f'- please avoid talking about the update or event in the main {chat_channel.mention}\n'
            f'  - if spoilers unavoidable by discussed topic use spoiler tags (||like this||) or spoiler blurs for images\n'
            f'- use {spoiler_channel.mention} (the channel you can access here) instead to talk about recent update\n'
            f'- this rule lasts for 48h after initial update/event release (will be removed <t:{until_unix}:R>)\n\n'
            f'ACCESS GRANT IS NOT UNDOABLE.\n'
            f'-# (it is but you\'ll have to ping me; you can\'t do it by yourself)\n'
            f'**IF YOU WISH TO NOT GET SPOILED ABOUT THE UPDATE OR EVENT, __DON\'T CLICK THIS__.**'
        )
        await access_msg.add_reaction('⚠️')

        # Send message in spoilers channel
        await spoiler_channel.send(f'# {event_name} started!')

        # Update state
        spoiler_state['active'] = True
        spoiler_state['until'] = until_dt.isoformat() # type: ignore
        spoiler_state['emoji'] = emoji
        spoiler_state['event_name'] = event_name
        spoiler_state['access_message_id'] = access_msg.id
        save_spoiler_state()

        await ctx.send(f'spoiler season started! ends <t:{until_unix}:R>')

    elif action == 'cancel':
        if not spoiler_state['active']:
            return await ctx.send('no active spoiler season')

        await end_spoiler_season()
        await ctx.send('spoiler season cancelled')

    elif action == 'rename':
        if len(args) < 2:
            return await ctx.send('usage: `.spoiler rename <emoji> <new_name>`')

        emoji = args[0]
        event_name = args[1]
        new_channel_name = f'{emoji}┃{event_name}-spoilers'
        await spoiler_channel.edit(name=new_channel_name)

        if spoiler_state['active']:
            spoiler_state['emoji'] = emoji
            spoiler_state['event_name'] = event_name
            save_spoiler_state()

        await ctx.send(f'renamed to `{new_channel_name}`')

    else:
        await ctx.send('invalid action')




async def stat_checker(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author

    total_points, challenges = calculate_points(member)
    ranked_leaderboard = get_ranked_leaderboard(ctx.guild)  # Use the new ranked leaderboard

    position_info = "*unranked*"
    for rank, points, members in ranked_leaderboard:
        if member in members:
            # If multiple members are tied at this rank, list them
            tied_members_mentions = [m.mention for m in members if m.id != member.id]
            if len(tied_members_mentions) > 1:
                # Format for display in .points command
                position_info = f'**#{rank}** (tied with {", ".join(tied_members_mentions)})'
            else:
                position_info = f'**#{rank}**'
            break

    challenge_list = '\n'.join([f'{i + 1}. <@&{role_id}>' for i, role_id in enumerate(challenges)])
    if not challenge_list:
        challenge_list = '*none*'

    response = (
        f'# {member.mention}\'s stats\n'
        f'total life savings `{total_points} pts`\n'
        f'leaderboard position: {position_info}\n'  # Updated line
        f'## completed challenge list\n'
        f'{challenge_list}'
    )

    await ctx.send(response, allowed_mentions=discord.AllowedMentions.none())


# @bot.command()
# @general.try_bot_perms
# async def points(ctx, member: discord.Member = None):
#     await stat_checker(ctx, member)
#
# @bot.command()
# @general.try_bot_perms
# async def pts(ctx, member: discord.Member = None):
#     await stat_checker(ctx, member)
#
# @bot.command()
# @general.try_bot_perms
# async def stats(ctx, member: discord.Member = None):
#     await stat_checker(ctx, member)

@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def pts(ctx, member: discord.Member = None):
    await stat_checker(ctx, member)


@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def complete(ctx, challenge_role: discord.Role, *members: discord.Member):
    if not members:
        return await ctx.send('usage: `.complete <challenge_role> <members...>`')

    # Verify it's a challenge role
    role_info = parse_challenge_role(challenge_role)
    if not role_info:
        return await ctx.send('that\'s not a challenge role')

    for member in members:
        await add_role(member, challenge_role.id)

    member_mentions = ', '.join([m.mention for m in members])
    await ctx.send(f'gave {challenge_role.mention} to {member_mentions}')


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles

        # Check for challenge role changes
        for role in added_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                emoji_map = {
                    '🟢': '<:yes:1454978155222663278>',
                    '⭐': '<:star_completion:1453452694592159925>',
                    '☄️': '<:star_pure_completion:1453452636618752214>'
                }
                emoji = emoji_map.get(role_info['tier_emoji'], '<:yes:1454978155222663278>')
                await general.send(bot,
                                   f'{emoji} {after.mention} completed **{role_info["name"]}** ({role_info["points"]} pts)')
                await update_leaderboard_message(bot, after.guild)

        for role in removed_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                await general.send(bot,
                                   f'<:no:1454950318042255410> {after.mention}\'s **{role_info["name"]}** completion was taken')
                await update_leaderboard_message(bot, after.guild)

        # [Keep all existing role update logic]
        for role in added_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('promotion', mention=after.mention))
                await general.send(bot, config.message('promotion_welcome', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('new_leader', mention=after.mention))
            if role.id == config.roles['inactive']:
                await general.send(bot, config.message('inactive', mention=after.mention))
            if role.id == config.roles['spoiler']:
                await general.send(bot, config.message('spoiler_add', mention=after.mention), 'spoiler')
            if role.id in config.roles['category:badges']['other']:
                await general.remove_role(after, config.roles['category:badges']['none'])
            if role.id in config.roles['category:misc']['other']:
                await general.remove_role(after, config.roles['category:misc']['none'])

        for role in removed_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('demotion', mention=after.mention))
                await general.send(bot, config.message('demotion_goodbye', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('leader_removed', mention=after.mention))
            if role.id == config.roles['newbie']:
                await general.send(bot, config.message('newbie', mention=after.mention))
            if role.id == config.roles['inactive']:
                await general.send(bot, config.message('inactive_revoke', mention=after.mention))
            if role.id == config.roles['spoiler']:
                await general.send(bot, config.message('spoiler_remove', mention=after.mention), 'spoiler')

        if any(role.id in config.roles['category:badges']['other'] for role in removed_roles):
            await activity.check_role_category(after, 'badges')
        if any(role.id in config.roles['category:misc']['other'] for role in removed_roles):
            await activity.check_role_category(after, 'misc')

    if before.nick != after.nick:
        old = before.nick if before.nick else before.display_name
        new = after.nick if after.nick else after.display_name
        await general.send(bot, config.message('name_change', mention=after.mention, old_name=old, new_name=new))



@bot.command()
@general.try_bot_perms
async def save(ctx, *args):
    if not args:
        return await ctx.send("usage: `.save [name] @member1 @member2 ...`")

    # Parse arguments - check if first arg is a member or a name
    save_name = None
    members = []

    for i, arg in enumerate(args):
        try:
            member = await commands.MemberConverter().convert(ctx, arg)
            members.append(member)
        except commands.MemberNotFound:
            # If it's the first argument, and we have no members yet, treat as name
            if i == 0 and not members:
                save_name = arg
            else:
                return await ctx.send(f"couldn't find member: `{arg}`")

    if not members:
        return await ctx.send("usage: `.save [name] @member1 @member2 ...`")

    return await create_save(ctx, members, save_name)


@bot.command()
@general.try_bot_perms
async def rename(ctx, name: str = None):
    await rename_save(ctx, name)


@bot.command()
async def disband(ctx):
    await disband_save(ctx)


@bot.command()
async def one_more(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/1426972811293098014/1438983499804708915/image.png?ex=6941bbd1&is=69406a51&hm=eb4a1cd864b53f8c9865afd49aec5dd6a54fed7c327bd262df17b69589bef0bb&')

@bot.command()
async def onemore(ctx):
    await ctx.send('https://cdn.discordapp.com/attachments/1426972811293098014/1438983499804708915/image.png?ex=6941bbd1&is=69406a51&hm=eb4a1cd864b53f8c9865afd49aec5dd6a54fed7c327bd262df17b69589bef0bb&')


@bot.command()
@general.try_bot_perms
#@general.inject_reply
async def van(ctx, member: discord.Member = None, *, reason: str = None):
    msg = f'{member.mention} has been vanned :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)

@bot.command()
@general.try_bot_perms
#@general.inject_reply
async def war(ctx, member: discord.Member = None, *, reason: str = None):
    msg = f'{member.mention} has been warred :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_messages')
async def pin(ctx):
    if not ctx.message.reference or not ctx.message.reference.resolved:
        return await ctx.send("you have to reply to a message to pin it")
    msg = ctx.message.reference.resolved
    return await msg.pin()

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_messages')
async def unpin(ctx):
    if not ctx.message.reference or not ctx.message.reference.resolved:
        return await ctx.send("you have to reply to a message to unpin it")
    msg = ctx.message.reference.resolved
    return await msg.unpin()

@bot.command()
@general.try_bot_perms
@general.has_perms('kick_members')
#@general.inject_reply
@general.can_moderate_member
async def kick(ctx, member: discord.Member = None, *, reason: str = None):
    await member.kick(reason=reason)

@bot.command()
@general.try_bot_perms
@general.has_perms('ban_members')
#@general.inject_reply
@general.can_moderate_member
async def ban(ctx, member: discord.Member = None, *, reason: str = None):
    await member.ban(reason=reason, delete_message_seconds=0)

@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
#@general.inject_reply
@general.can_moderate_member
async def mute(ctx, member: discord.Member = None, duration: str = None, *, reason: str = None):
    if not duration:
        await ctx.send('u forgot to specify duration bro. i gotchu tho. default value is 5 min')
        duration = '5m'

    timeout_duration = moderation.get_timeout_duration(duration)
    await member.timeout(timeout_duration, reason=reason)

    formatted_duration = moderation.format_timedelta(timeout_duration)
    await ctx.send(f"muted the guy for {formatted_duration} :white_check_mark:")

@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
#@general.inject_reply
@general.can_moderate_member
async def unmute(ctx, member: discord.Member = None, *, reason: str = None):
    await moderation.unmute(ctx, member, reason)

@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
#@general.inject_reply
@general.can_moderate_member
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    await moderation.warn(ctx, member, reason)

@bot.command()
@general.try_bot_perms
#@general.inject_reply
async def warns(ctx, member: discord.Member = None):
    if member.guild.get_role(config.roles['warn_1']) in member.roles:
        await ctx.send(f"this guy has 1 warn :yellow_circle:")
    elif member.guild.get_role(config.roles['warn_2']) in member.roles:
        await ctx.send(f"this guy has 2 warns :orange_circle:")
    elif member.guild.get_role(config.roles['warn_3']) in member.roles:
        await ctx.send(f"this guy has 3 warns :red_circle:\n-# next warn will ban them btw")
    else:
        await ctx.send(f"this guy doesn't have warns they're an outstanding citizen :white_check_mark:")

@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
#@general.inject_reply
@general.can_moderate_member
async def clear_warns(ctx, member: discord.Member = None):
    await member.timeout(None)
    await general.remove_role(member, general.config.roles['warn_1'])
    await general.remove_role(member, general.config.roles['warn_2'])
    await general.remove_role(member, general.config.roles['warn_3'])
    await ctx.send(f"cleared all warns :white_check_mark:")

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_channels')
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(config.message("channel_lock"))

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_channels')
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send(config.message("channel_unlock"))





from discord.ui import View, button
class ConfirmDeleteView(View):
    def __init__(self, author: discord.User):
        super().__init__(timeout=30)
        self.author = author
        self.result = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.defer(ephemeral=True) # type: ignore
            await interaction.followup.send("this confirmation ain't for you pal", ephemeral=True)
            return False
        return True

    @button(label="proceed", style=discord.ButtonStyle.danger) # type: ignore
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        await interaction.message.edit(content=":wastebasket: proceeding with deletion...", view=None)
        self.stop()

    @button(label="cancel", style=discord.ButtonStyle.secondary) # type: ignore
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        await interaction.message.edit(content="❌ deletion canceled", view=None)
        self.stop()



@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def start_loop(ctx):
    await ctx.message.delete()
    await send_timed_delete_msg(bot, 'got it', 3)
    member_checker.start()

@bot.command()
@general.has_perms('manage_messages')
@general.try_bot_perms
async def r(ctx, start_id: int, end_id: int = None):
    channel = ctx.channel
    await ctx.message.delete()

    res_msg = await ctx.send(f':brain: finding messages to delete')

    if end_id is None:
        if start_id > 30:
            return await general.timed_delete_msg(res_msg, 'u tried to delete >30 msgs with recent deletion, make sure u doin the right thing. to delete more than 30 use message ids')

        messages = []
        async for msg in channel.history(limit=start_id+1):  # +1 to skip the res_msg
            if msg.id != res_msg.id:
                messages.append(msg)

        await channel.delete_messages(messages)
        return await timed_delete_msg(res_msg, f'deleted {len(messages)} recent messages', 5)

    else:
        try:
            start_message = await channel.fetch_message(start_id)
            end_message = await channel.fetch_message(end_id)
        except discord.NotFound:
            return await timed_delete_msg(res_msg, 'one of the message ids wasn\'t found, make sure u doin the right thing', 10)
        except discord.HTTPException as e:
            return await timed_delete_msg(res_msg, f'unable to fetch msgs: {e}', 10)

        if start_message.created_at > end_message.created_at:
            start_message, end_message = end_message, start_message

        await res_msg.edit(content=':brain: selecting messages to delete')
        messages_to_delete = []
        async for message in channel.history(
            limit=None,
            before=end_message.created_at,
            after=start_message.created_at,
        ):
            messages_to_delete.append(message)

        if start_message not in messages_to_delete:
            messages_to_delete.append(start_message)
        if end_message not in messages_to_delete:
            messages_to_delete.append(end_message)

        await res_msg.edit(content=':brain: sorting messages to delete')
        messages_to_delete.sort(key=lambda m: m.created_at)

        if not messages_to_delete:
            return await timed_delete_msg(res_msg, f'there are no messages between those ids', 10)


        total_to_delete = len(messages_to_delete)
        if total_to_delete > 50:
            view = ConfirmDeleteView(ctx.author)
            await res_msg.edit(content=f'⚠️ ur about to delete **{total_to_delete} messages**. u sure?', view=view)
            await view.wait()

            if view.result is None or not view.result:
                return await timed_delete_msg(res_msg, 'deletion cancelled', 10)


        total_deleted = 0
        message_chunks = [messages_to_delete[i:i + 100] for i in range(0, len(messages_to_delete), 100)]

        for chunk in message_chunks:
            await res_msg.edit(content=f':wastebasket: deleting {len(chunk)} messages (total so far: {total_deleted}) (total to delete: {len(messages_to_delete)})')
            await channel.delete_messages(chunk)
            total_deleted += len(chunk)
            await asyncio.sleep(1)

        return await timed_delete_msg(res_msg, f'deleted {total_deleted} messages', 10)



import subprocess
@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def update(ctx):
    await ctx.send(':radio_button: pulling from git...')
    try:
        result = subprocess.run(
            ['git', 'pull'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return await ctx.send(f':warning: git pull failed\n```{result.stderr}```')
        await ctx.send(f'```{result.stdout}```')
        await ctx.send(f':radio_button: restarting bot...')
        subprocess.Popen(['systemctl', 'restart', '--user', 'tcs-utils-dcbot'])

    except subprocess.TimeoutExpired:
        await ctx.send(':x: git pull timed out')
    except Exception as e:
        await ctx.send(f':x: error: ```{e}```')


@bot.command()
@general.try_bot_perms
@general.work_in_progress
async def br(ctx):
    return await ctx.reply('sry fam ts command no workie and im too lazy to fix it so its cancelled for now')


@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def check_inactive(ctx, member: discord.Member):
    chat_channel = ctx.guild.get_channel(config.channels['chat'])
    bot_msg = await ctx.send('🤔 checking past activity...')

    last_message = None
    last_bot_mention = None

    checked_msg = 0
    await bot_msg.edit(content='🤔 fetching 15000 messages from chat...')
    async for msg in chat_channel.history(limit=15000):
        checked_msg += 1
        if (checked_msg % 750) == 0:
            await bot_msg.edit(content=f'🤔 checking msg `{checked_msg}`/`10000`...'
                                       f'{f'\n- last message: <t:{int(last_message.created_at.timestamp())}:R> ([jump]({last_message.jump_url}))' if last_message else '\n- last message: *searching*'}'
                                       f'{f'\n- last mention by bot (availability/vc changes): <t:{int(last_bot_mention.created_at.timestamp())}:R> ([jump]({last_bot_mention.jump_url}))' if last_bot_mention else '\n- last mention by bot (availability/vc changes): *searching*'}')
        if msg.author == member and not last_message:
            last_message = msg
        if msg.author == bot.user and member.display_name in msg.content and not last_bot_mention:
            last_bot_mention = msg
        if last_message and last_bot_mention:
            break

    response = f"🔥 **{member.mention}'s activity over the past 10000 messages**\n"

    if last_message:
        response += f"- last message: <t:{int(last_message.created_at.timestamp())}:R> ([jump]({last_message.jump_url}))\n"
    else:
        response += "- last message: *none*\n"

    if last_bot_mention:
        response += f"- last mention by bot (availability/vc changes): <t:{int(last_bot_mention.created_at.timestamp())}:R> ([jump]({last_bot_mention.jump_url}))"
    else:
        response += "- last mention by bot (availability/vc changes): *none*"

    await bot_msg.edit(content=response)



@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def check_inactive_people(ctx):
    await activity.check_inactivity(bot)




@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def inactive(ctx, member: discord.Member):
    await general.add_role(member, config.roles['inactive'])


@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def unavailable(ctx, member: discord.Member):
    channel = bot.get_channel(config.channels['availability'])
    msg = await channel.fetch_message(config.channels['availability_message'])

    await msg.remove_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), member)

    return await general.send(bot, config.message('unavailable_auto', name=member.mention,
                       available_count=f"{general.emojify(str(await activity.count_available(bot)), 'b')}"))


async def remove_availability(member):
    channel = bot.get_channel(config.channels['availability'])
    msg = await channel.fetch_message(config.channels['availability_message'])

    await msg.remove_reaction(discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'),
                              member)

    return await general.send(bot, config.message('unavailable_auto', name=member.mention,
                                                  available_count=f"{general.emojify(str(await activity.count_available(bot)), 'b')}"))

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def clean_availability(ctx):
    await check_availability(bot)
    
    
    
# @bot.command()
# async def br(ctx, *args):
#     # if not ctx.guild.get_role(ROLES['mod']) not in ctx.author.roles:
#     #     return await ctx.send(message("nuh_uh"))
#     parsed_args = list(args)
#     if len(parsed_args) == 0:
#         return await ctx.send(
#             'usage `.br <challenge> [best?] <route> <death-floor> <death-door> [flag][participants] -- <reason>`\n'
#             'format `.br <tcs/gor/pdo> [b] bh[ro]m[-l] <b/h/r/o/m> (int) [-l @leader] [-d @dead_member] [-x @disconnected_member] [@normal_member] ... -- (str)`\n'
#             'death-door argument can also represent death meters in outdoors if death-floor is \'o\'\n'
#             '-l at the end of route means long rooms and only works if r is included. long rooms means up to a-1000, short rooms means up to a-200'
#         )
#
#     run_type = parsed_args.pop(0).lower()
#     if run_type not in config.emoji:
#         return await ctx.send(
#             f'invalid challenge `{run_type}`'
#         )
#
#     new_best = False
#     if len(parsed_args) >= 1 and parsed_args[0] == 'b':
#         new_best = True
#         parsed_args.pop(0)
#
#     if len(parsed_args) < 3:  # minimum route, death-floor, death-door
#         return await ctx.send('wrong usage :wilted_rose:')
#
#     route = parsed_args[0]
#     death_floor = parsed_args[1]
#     try:
#         death_time = int(parsed_args[2])
#     except ValueError:
#         await ctx.send(
#             'wrong death door it has to be an integer :wilted_rose:'
#         )
#         return None
#
#     death_point = (death_floor, death_time)
#
#     # Find the separator for reason
#     try:
#         reason_separator_index = parsed_args.index('--', 3)
#     except ValueError:
#         return await ctx.send(
#             'pls tell me the run failure reason after `--`'
#         )
#
#     # Extract participant arguments and reason
#     participant_args = parsed_args[3:reason_separator_index]
#     reason = ' '.join(parsed_args[reason_separator_index + 1 :])
#
#     if not reason:
#         return await ctx.send('how tf did u fail? tell me! after `--` at the end of the command')
#
#     from best_runs import RunMember, RunDetails
#     participants: list[RunMember] = []
#
#     # Helper to create a RunMember from a discord.Member
#     async def create_run_member(member: discord.Member):
#         return RunMember(
#             member=member,
#             is_leader=current_member_flags['is_leader'],
#             is_dead=current_member_flags['is_dead'],
#             is_disconnected=current_member_flags['is_disconnected'],
#         )
#
#     current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}
#     # Process participant arguments
#     for arg in participant_args:
#         if arg == '-l':
#             current_member_flags['is_leader'] = True
#         if arg == '-d':
#             current_member_flags['is_dead'] = True
#         if arg == '-x':
#             current_member_flags['is_disconnected'] = True
#         if arg not in ['-x', '-d', '-l']:
#             try:
#                 # Resolve member from mention (e.g., <@123456789>)
#                 member = await commands.MemberConverter().convert(ctx, arg)
#                 participants.append(await create_run_member(member))
#                 current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}
#             except commands.MemberNotFound:
#                 await ctx.send(f'Could not find member: `{arg}`')
#             finally:
#                 # Reset flags after adding a member or if it's not a flag
#                 current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}
#
#     run_details = RunDetails(
#         run_type=run_type,
#         route=route,
#         death_point=death_point,
#         reason=reason,
#         participants=participants,
#         is_new_best=new_best,
#     )
#     return await ctx.send(run_details.message_text)


if __name__ == '__main__':
    bot.run(config.TOKEN)