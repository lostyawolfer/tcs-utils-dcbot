import asyncio

import discord
from discord.ext import commands, tasks
from modules import config, activity, moderation, general, badges
from modules.general import timed_delete_msg, send_timed_delete_msg
from modules.role_management import RoleSession
from modules.saves import create_save, disband_save, rename_save
from modules.points import calculate_points, get_ranked_leaderboard, update_leaderboard_message, parse_challenge_role, get_member_rank, has_all_challenges, LB_EMOJI
from modules.bot_init import bot


################################################################

version = 'v4.3.0'

changelog = \
    f"""
:tada: **{version} changelog**
- you can now choose to show your leaderboard position in <#1468068634680229979>
- changing leaderboard positions now sends messages in chat
- automatic adding of special roles and announcement of when someone completes all base or ultimate challenges
- the leaderboard channel now uses the custom emoji for top-3 instead of base ones
"""
# changelog = 'not sending changelog because fuck you' # type: ignore

################################################################



@tasks.loop(minutes=45)
async def member_checker():
    await activity.check_all_members()
    await activity.run_activity_checks()


@bot.event
async def on_ready():
    await general.send(f':radio_button: bot connected... {version}')
    await general.set_status('starting up...', status=discord.Status.idle) # type: ignore
    await bot.wait_until_ready()
    await general.send(f':ballot_box_with_check: restart complete!')
    await general.send(changelog)
    bot.add_view(badges.WardrobeOpenView())
    await badges.ensure_wardrobe_message(bot)
    await activity.sync_interested_reactions()
    msg = await general.send(f':eye: lemme build up some activity cache...')
    await activity.build_activity_cache()
    await msg.reply(':white_check_mark: activity cache built, gonna run activity checks every 45 mintues')
    if not member_checker.is_running():
        member_checker.start()


@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def force_check_all(ctx):
    member_checker.stop()
    member_checker.start()

@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def check(ctx, member: discord.Member = None):
    async with RoleSession(member) as rs:
        await activity.full_check_member(rs, member)
        await send_timed_delete_msg(f'checked {member.display_name}')

@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def test(ctx):
    await ctx.send(f'test pass\n-# {version}')

@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def force_reactions(ctx):
    await activity.sync_interested_reactions()
    await ctx.send('uh huh')




@bot.event
async def on_voice_state_update(member, before, after):
    if not config.check_guild(member.guild.id) or member.bot:
        return

    activity.update_cache(member.id)

    vc1 = member.guild.get_channel(config.channels['vc'])
    vc2 = member.guild.get_channel(config.channels['vc2'])
    vc3 = member.guild.get_channel(config.channels['vc3'])

    channel_info = {
        vc1: {
            'in_vc': 'in_vc',
            'join_msg': 'join_vc',
            'leave_msg': 'leave_vc',
            'color': 'g',
        },
        vc2: {
            'in_vc': 'in_vc_2',
            'join_msg': 'join_vc_2',
            'leave_msg': 'leave_vc_2',
            'color': 'p',
        },
        vc3: {
            'in_vc': 'in_vc_3',
            'join_msg': 'join_vc_3',
            'leave_msg': 'leave_vc_3',
            'color': 'r',
        },
    }

    messages = []

    async with RoleSession(member) as rs:
        # leaving
        if before.channel in channel_info and before.channel != after.channel:
            info = channel_info[before.channel]

            messages.append(config.message(
                info['leave_msg'],
                member=member.mention,
                count=general.emojify(
                    str(len(before.channel.members)),
                    info['color'],
                ),
            ))

            rs.remove(info['in_vc'])

        # joining
        if after.channel in channel_info and before.channel != after.channel:
            info = channel_info[after.channel]

            messages.append(config.message(
                info['join_msg'],
                member=member.mention,
                count=general.emojify(
                    str(len(after.channel.members)),
                    info['color'],
                ),
            ))

            rs.add(info['in_vc'])

    if messages:
        await member.guild.get_channel(
            config.channels['chat']
        ).send(
            '\n'.join(messages),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    await general.update_status(bot)


# Reaction Roles - easy hot-swap
REACTION_ROLES = {
    1451676590558937221: {  # message_id
        "⚠️": 1451675068114669740,  # emoji: role_id
    }
}


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    activity.update_cache(payload.user_id)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    async with RoleSession(member) as rs:
        # availability logic
        if payload.message_id == config.channels['availability_message']:
            if payload.emoji.id == config.channels['availability_reaction']:
                await activity.add_availability(rs, member)

        # interested roles logic (tiered) - don't commit immediately
        interested_msgs = [
            activity.INTERESTED_MESSAGE_BASE,
            activity.INTERESTED_MESSAGE_STAR,
            activity.INTERESTED_MESSAGE_ULTIMATE
        ]
        if payload.message_id in interested_msgs:
            role_map = activity.get_interested_role_map(guild, payload.message_id)
            emoji_str = str(payload.emoji)
            if emoji_str in role_map:
                role = role_map[emoji_str]

                # track initial state if first change
                if payload.user_id not in activity.user_initial_states:
                    activity.user_initial_states[payload.user_id] = {
                        r for r in role_map.values() if r in member.roles
                    }

                # update debounce state
                state = activity.user_pending_changes.setdefault(
                    payload.user_id, {'added': set(), 'removed': set()}
                )
                state['added'].add(role)
                state['removed'].discard(role)
                await activity.schedule_interested_debounce(payload.user_id, guild)
                return  # don't commit yet

        # static reaction roles
        if payload.message_id in REACTION_ROLES:
            emoji_str = str(payload.emoji)
            if emoji_str in REACTION_ROLES[payload.message_id]:
                rs.add(REACTION_ROLES[payload.message_id][emoji_str])


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id: return
    activity.update_cache(payload.user_id)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    async with RoleSession(member) as rs:
        # availability logic
        if payload.message_id == config.channels['availability_message']:
            if payload.emoji.id == config.channels['availability_reaction']:
                await activity.remove_availability(rs, member)

        # interested roles logic (tiered) - don't commit immediately
        interested_msgs = [
            activity.INTERESTED_MESSAGE_BASE,
            activity.INTERESTED_MESSAGE_STAR,
            activity.INTERESTED_MESSAGE_ULTIMATE
        ]
        if payload.message_id in interested_msgs:
            role_map = activity.get_interested_role_map(guild, payload.message_id)
            emoji_str = str(payload.emoji)
            if emoji_str in role_map:
                role = role_map[emoji_str]

                # track initial state if first change
                if payload.user_id not in activity.user_initial_states:
                    activity.user_initial_states[payload.user_id] = {
                        r for r in role_map.values() if r in member.roles
                    }

                # update debounce state
                state = activity.user_pending_changes.setdefault(
                    payload.user_id, {'added': set(), 'removed': set()}
                )
                state['removed'].add(role)
                state['added'].discard(role)
                await activity.schedule_interested_debounce(payload.user_id, guild)
                return  # don't commit yet

        # static reaction roles
        if payload.message_id in REACTION_ROLES:
            emoji_str = str(payload.emoji)
            if emoji_str in REACTION_ROLES[payload.message_id]:
                rs.remove(REACTION_ROLES[payload.message_id][emoji_str])

async def remove_availability_auto(member):
    channel = bot.get_channel(config.channels['availability'])
    msg = await channel.fetch_message(config.channels['availability_message'])
    reaction_flag = False
    for reaction in msg.reactions:
        if reaction.emoji == discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'):
            async for user in reaction.users():
                if user == member:
                    reaction_flag = True
                    break

    async with RoleSession(member) as rs:
        rs.remove(config.roles['available'])
    if reaction_flag:
        await msg.remove_reaction(
            discord.PartialEmoji(id=config.channels['availability_reaction'], name='available'), member)
        await general.send(config.message('unavailable_auto', name=member.mention,
                                               available_count=f"{general.emojify(str(await activity.count_available(bot)), 'b')}"),
                                               pings=discord.AllowedMentions.none())


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles

        # track old rank before any leaderboard update
        old_rank = None
        challenge_changed = False

        for role in added_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                challenge_changed = True
                if old_rank is None:
                    old_rank = get_member_rank(after.guild, after)

                emoji_map = {
                    '🟢': '<:yes:1463357188964618413>',
                    '⭐': '<:star_completion:1453452694592159925>',
                    '☄': '<:star_pure_completion:1453452636618752214>'
                }
                emoji = emoji_map.get(role_info['tier_emoji'], '<:yes:1463357188964618413>')
                announce = 'completed a custom challenge' if not role.name.startswith('🏆') else 'completed'
                await general.send(
                    f'{emoji} {after.mention} {announce} **{role_info["name"]}** ({role_info["points"]} pts)')

        for role in removed_roles:
            role_info = parse_challenge_role(role)
            if role_info:
                challenge_changed = True
                if old_rank is None:
                    old_rank = get_member_rank(after.guild, after)

                announce = '(custom challenge) ' if not role.name.startswith('🏆') else ''
                await general.send(
                    f'<:no:1454950318042255410> {after.mention}\'s **{role_info["name"]}** {announce}completion was taken')

        # update leaderboard and check for rank changes
        if challenge_changed:
            await update_leaderboard_message(bot, after.guild)
            new_rank = get_member_rank(after.guild, after)

            if old_rank != new_rank and new_rank is not None:
                emoji = LB_EMOJI.get(new_rank, "🏆")
                await general.send(
                    f"{emoji} {after.mention}'s leaderboard position is now **#{new_rank}**!"
                )

        # check completion roles
        async with RoleSession(after) as rs:
            had_all_base = config.roles["completion_all_base"] in before_roles
            has_all_base = has_all_challenges(after, {"🟢"})

            if has_all_base and not had_all_base:
                rs.add(config.roles["completion_all_base"])
                await general.send(
                    f"{config.emoji['star_completion']} {after.mention} beat **all base challenges**!"
                )

            had_all_ultimate = config.roles["completion_all_ultimate"] in before_roles
            has_all_ultimate = has_all_challenges(after, {"⭐", "☄"})

            if has_all_ultimate and not had_all_ultimate:
                rs.add(config.roles["completion_all_ultimate"])
                await general.send(
                    f"{config.emoji['star_pure_completion']} {after.mention} beat **all ultimate challenges**!"
                )

        for role in added_roles:
            if role.id == config.roles['mod']:
                await general.send(config.message('promotion', mention=after.mention))
                await general.send(config.message('promotion_welcome', mention=after.mention), 'mod_chat')
            elif role.id == config.roles['leader']:
                await general.send(config.message('new_leader', mention=after.mention))
            elif role.id == config.roles['inactive']:
                await general.send(config.message('inactive', mention=after.mention))
            elif role.id == config.roles['explained_inactive']:
                await general.send(config.message('explained_inactive', mention=after.mention))
            elif role.id == config.roles['spoiler']:
                await general.send(config.message('spoiler_add', mention=after.mention), 'spoiler')

        for role in removed_roles:
            if role.id == config.roles['mod']:
                await general.send(config.message('demotion', mention=after.mention))
                await general.send(config.message('demotion_goodbye', mention=after.mention), 'mod_chat')
            elif role.id == config.roles['leader']:
                await general.send(config.message('leader_removed', mention=after.mention))
            elif role.id == config.roles['newbie']:
                await general.send(config.message('newbie', mention=after.mention))
            elif role.id == config.roles['inactive']:
                await general.send(config.message('inactive_revoke', mention=after.mention))
            elif role.id == config.roles['spoiler']:
                await general.send(config.message('spoiler_remove', mention=after.mention), 'spoiler')
            elif role.id == config.roles['available']:
                await remove_availability_auto(after)

    if before.nick != after.nick:
        old = before.nick if before.nick else before.display_name
        new = after.nick if after.nick else after.display_name
        await general.send(config.message('name_change', mention=after.mention, old_name=old, new_name=new))

    session = RoleSession(after)
    await session.commit()


@bot.event
async def on_member_join(member):
    guild = member.guild
    if not config.check_guild(guild.id):
        return

    async with RoleSession(member) as rs:
        if member.bot:
            await general.send(config.message('join_bot', mention=member.mention))
            rs.add('bot')
        else:
            await general.send(config.message('join', mention=member.mention))
            await general.send(msg='-# read below for just a quick tour around :3\n'
                                        '-# channels you really should check out: <#1442604555798974485> <#1426974985402187776> <#1464608724667858975>\n'
                                        '-# grab <#1434653852367585300> when you are ready to play! (don\'t forget to remove it when you stop being available!)\n'
                                        '-# join <#1426974154556702720> at any time!\n'
                                        '-# please respect others and remain active! unexplained long inactivity is something very frowned upon here')
            await general.send(f':new: <@&{config.roles['mod']}> hey, we got a new member in the server! nice work! a friendly reminder to set their nickname to their roblox display name :3', 'mod_chat')

            for role in config.roles['new_people']:
                rs.add(role)



@bot.event
async def on_member_remove(member):
    guild = member.guild
    if not config.check_guild(guild.id):
        return

    if member.bot:
        await general.send(config.message('kick_bot', mention=member.mention))

    else:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await general.send(config.message('kick', mention=member.mention))
                    return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target == member and \
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    await general.send(config.message('ban', mention=member.mention))
                    return

        await general.send(config.message('leave', mention=member.mention))


import re

# async def log_message(message: discord.Message):
#     if message.channel.id == config.channels['logs_channel']:
#         return
#
#     print(f'#{message.channel.name} | @{message.author.display_name} >> {message.content}')
#
#     channel = bot.get_channel(config.channels['logs_channel'])
#     timestamp = f"<t:{int(message.created_at.timestamp())}:f>"
#     content = message.content
#
#     if not content.strip() and not message.attachments and not message.stickers:
#         content = "*[no visible content]*"
#
#     log_message = (
#         f'### {message.channel.mention} >> {message.author.mention} — {timestamp}\n'
#         f'{content}\n'
#     )
#
#     attachment_urls = [attachment.url for attachment in message.attachments]
#     if attachment_urls:
#         log_message += "\n" + "\n".join(attachment_urls)
#
#     await channel.send(log_message, allowed_mentions=discord.AllowedMentions.none(), silent=True,
#                        stickers=message.stickers)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.guild:
        activity.update_cache(message.author.id)

    if '<#1426974154556702720>' in message.content or message.content.lower() == 'ps':
        await message.channel.send(
            f'link: **https://www.roblox.com/share?code=1141897d2bd9a14e955091d8a4061ee5&type=Server**',
            suppress_embeds=True)

    if 'nigga' in message.content.lower() or 'nigger' in message.content.lower():
        await message.channel.send(
            '[[<@534097411048603648>]] i will personally fix ur fucking skin color if you say that word again')

    if 'one more' in message.content.lower():
        await message.channel.send(
            'https://cdn.discordapp.com/attachments/1426972811293098014/1438983499804708915/image.png?ex=6941bbd1&is=69406a51&hm=eb4a1cd864b53f8c9865afd49aec5dd6a54fed7c327bd262df17b69589bef0bb&'
        )

    if 'npc' == message.content.lower():
        await message.reply('yep thats me', allowed_mentions=discord.AllowedMentions.none())

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


@bot.command()
@general.try_bot_perms
async def points(ctx, member: discord.Member = None):
    await stat_checker(ctx, member)


@bot.command()
@general.try_bot_perms
async def pts(ctx, member: discord.Member = None):
    await stat_checker(ctx, member)


@bot.command()
@general.try_bot_perms
async def stats(ctx, member: discord.Member = None):
    await stat_checker(ctx, member)


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
@general.try_bot_perms
async def van(ctx, member: discord.Member = None, *, reason: str = None):
    msg = f'{member.mention} has been vanned :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)


@bot.command()
@general.try_bot_perms
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
@general.can_moderate_member
async def kick(ctx, member: discord.Member = None, *, reason: str = None):
    await member.kick(reason=reason)


@bot.command()
@general.try_bot_perms
@general.has_perms('ban_members')
@general.can_moderate_member
async def ban(ctx, member: discord.Member = None, *, reason: str = None):
    await member.ban(reason=reason, delete_message_seconds=0)


@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
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
@general.can_moderate_member
async def unmute(ctx, member: discord.Member = None, *, reason: str = None):
    await moderation.unmute(ctx, member, reason)


@bot.command()
@general.try_bot_perms
@general.has_perms('moderate_members')
@general.can_moderate_member
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    await moderation.warn(ctx, member, reason)


@bot.command()
@general.try_bot_perms
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
@general.can_moderate_member
async def clear_warns(ctx, member: discord.Member = None):
    await member.timeout(None)
    async with RoleSession(member) as rs:
        rs.remove(general.config.roles['warn_1'])
        rs.remove(general.config.roles['warn_2'])
        rs.remove(general.config.roles['warn_3'])
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


@bot.command()
@general.try_bot_perms
@general.has_perms('owner')
async def update(ctx):
    import subprocess
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
@general.has_perms('manage_roles')
async def check_inactive_people(ctx):
    await activity.check_inactivity()


@bot.command()
@general.try_bot_perms
@general.has_perms('manage_roles')
async def unavailable(ctx, member: discord.Member):
    await remove_availability_auto(member)


if __name__ == '__main__':
    bot.run(config.TOKEN)