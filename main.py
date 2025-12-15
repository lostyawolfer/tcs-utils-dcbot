import datetime
import discord
from discord.ext import commands, tasks
from modules import config, availability_vc, moderation, general
from modules.saves import create_save, disband_save

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)


@tasks.loop(hours=3)
async def status_updater_loop():
    await availability_vc.check_all_members(bot)


version = 'v2.6'
changelog = \
f"""
:tada: **{version} changelog**
- added `.help` command to list every single available command in the bot
- `.mute` command now has a default duration of 5 minutes because ppl seemed to always forget duration was a thing to include
- added a new `.van` ahh command
- added a reminder in mod chat to set ppl's names to their roblox ones when they join
- if the bot encounters any errors during command execution it will ping the bot's maintainer
"""
@bot.event
async def on_ready():
    await general.send(bot, f':radio_button: bot connected... {version}')
    await general.set_status(bot, 'starting up...', status=discord.Status('idle'))
    await bot.wait_until_ready()
    await availability_vc.check_all_members(bot)
    await general.send(bot, f':ballot_box_with_check: restart complete!')
    await general.send(bot, changelog)

@bot.command()
@general.has_perms('manage_roles')
@general.try_bot_perms
async def check_members(ctx):
    await availability_vc.check_all_members(bot)

@bot.command()
@general.try_bot_perms
async def test(ctx):
    await ctx.send(f'test pass\n-# {version}')



help_text_intro = \
"""
# help center
-# `<``>` means required arg, `[``]` means optional arg
-# `*` permission means "everyone" or "no special permissions required"
-# you cannot moderate members same or higher in role hierarchy than you, yourself, the owner and the bot 
-# if the bot sends an image of jevil on a wheelchair saying "i can't do anything", this means the bot's code is garbage, and it ran into an error.
-# usually the bot will ping its maintainer on its own, but if for some reason it doesn't, do it yourself, please :3
"""

help_text_public = \
"""
## public commands
- `.test` - test if the bot is alive; see current version
- `.help` - see this list
- `.save <@members...>` - creates a private channel and role for the mentioned members, useful for coordinating save continuations - perms: `*`
- `.disband` - used in a save-type channel, deletes the save role and its channel - perms: `*`
"""

help_text_admin = \
"""
## admin commands
- `.ban <@member> [reason]` - bans the member. reason is only for audit log - perms: `ban members`
- `.kick <@member> [reason]` - kicks the member. reason is only for audit log - perms: `kick members`
- `.warn <@member> [reason]` - upgrades the member's current warn role or gives them one, then mutes or bans them accordingly (read <#1442604555798974485>) - perms: `moderate members`
- `.mute <@member> [duration]` - times the member out with native discord tools. time format: Ns, Nm, Nh or Nd with N being an integer. default duration is 5m. - perms: `moderate members`
- `.unmute <@member>` - clears any timeouts the member has - perms: `moderate members`
- `.clear_warns <@member>` - clears timeouts and all warn roles from a member - perms: `moderate members`
- `.warns <@member>` - just sends the member's current top warn role - perms: `*`
- `.check_members` - starts the usual member checking process that usually happens automatically every 3 hours or on bot startup. member checking includes fixing category roles, checking consistency of availability and in vc roles, and removing the newbie role from those who were on the server for more than 7 days. takes around 4 minutes on average to complete - perms: `manage roles`
- ~~`.check_newbies`~~ - DEPRECATED - use `.check_members` instead
- ~~`.br`~~ - UNAVAILABLE
"""

help_text_owner = \
"""
## owner only commands
- `.update` - server-side, pulls source git updates from remote, and restarts the systemctl - perms: `owner`
- `.lock` - locks down the channel it was written in, so no one can send messages in it - perms: `owner`
- `.unlock` - unlocks the `.lock`ed channel - perms: `owner`
- `.r <from_id> <to_id>` - clears up all the messages in the range of specified ids - perms: `owner`
"""

help_text_fun = \
"""
## fun stuff!
- `.van <@member> [reason]` - joke. a misspelling of the command `.ban`. "vans" the member (does literally nothing except send a message about it). - perms: `*`
- `.war <@member> [reason]` - joke. literally same as `.van` but a misspelling of `.warn` instead - perms: `*`
"""

@bot.command()
@general.try_bot_perms
async def help(ctx):
    await ctx.send(help_text_intro)
    await ctx.send(help_text_public)
    await ctx.send(help_text_admin)
    await ctx.send(help_text_owner)
    await ctx.send(help_text_fun)

@bot.event
async def on_voice_state_update(member, before, after):
    if not config.check_guild(member.guild.id) or (member and member.bot):
        return
    await availability_vc.voice_check(bot, member)


@bot.event
async def on_raw_reaction_add(payload):
    member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
    if not config.check_guild(payload.guild_id) or (member and member.bot):
        return
    if payload.message_id == config.channels['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == config.channels['availability_reaction']:
            await availability_vc.add_availability(bot, bot.get_guild(payload.guild_id).get_member(payload.user_id))


@bot.event
async def on_raw_reaction_remove(payload):
    member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
    if not config.check_guild(payload.guild_id) or (member and member.bot):
        return
    if payload.message_id == config.channels['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == config.channels['availability_reaction']:
            await availability_vc.remove_availability(bot, bot.get_guild(payload.guild_id).get_member(payload.user_id))


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles
        for role in added_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('promotion', mention=after.mention))
                await general.send(bot, config.message('promotion_welcome', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('new_leader', mention=after.mention))
            if role.id == config.roles['inactive']:
                await general.send(bot, config.message('inactive', mention=after.mention))

            if role.id == config.roles['completion_tbs']:
                await general.send(bot, config.message('completion_tbs', mention=after.mention))
            if role.id == config.roles['completion_ahp']:
                await general.send(bot, config.message('completion_ahp', mention=after.mention))
            if role.id == config.roles['completion_star']:
                await general.send(bot, config.message('completion_star', mention=after.mention))
            if role.id == config.roles['completion_dv']:
                await general.send(bot, config.message('completion_dv', mention=after.mention))
            if role.id == config.roles['completion_ch_tcs']:
                await general.send(bot, config.message('completion_ch_tcs', mention=after.mention))
            if role.id == config.roles['completion_ch_gor']:
                await general.send(bot, config.message('completion_ch_gor', mention=after.mention))
            if role.id == config.roles['completion_ch_pdo']:
                await general.send(bot, config.message('completion_ch_pdo', mention=after.mention))
            if role.id == config.roles['completion_ch_nn']:
                await general.send(bot, config.message('completion_ch_nn', mention=after.mention))

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

        if any(role.id in config.roles['category:badges']['other'] for role in removed_roles):
            await availability_vc.check_role_category(after, 'badges')
        if any(role.id in config.roles['category:misc']['other'] for role in removed_roles):
            await availability_vc.check_role_category(after, 'misc')

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
                                    '-# please respect others and remain active! random long inactivity is something very frowned upon here')
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
@bot.event
async def on_message(message: discord.Message):
    print(f'#{message.channel.name} | @{message.author.display_name} >> {message.content}')
    if message.author == bot.user:
        return
    if '<#1426974154556702720>' in message.content or 'ps' in re.findall(r"\b\w+\b", message.content.lower()):
        await message.channel.send(f'link: **https://www.roblox.com/share?code=1141897d2bd9a14e955091d8a4061ee5&type=Server**', suppress_embeds=True)
    if 'nigga' in message.content.lower() or 'nigger' in message.content.lower():
        await message.channel.send(f'[[<@534097411048603648>]] i will personally fix ur fucking skin color if you say that word again')
    await bot.process_commands(message)


@general.try_bot_perms
@bot.command()
async def save(ctx, *members: discord.Member):
    if not members:
        return await ctx.send("usage: `.save @member1 @member2 ...`")
    return await create_save(ctx, list(members))


@bot.command()
async def disband(ctx):
    await disband_save(ctx)


@bot.command()
@general.try_bot_perms
async def van(ctx, member: discord.Member, *, reason: str = None):
    msg = f'{member.mention} has been vanned :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)

@bot.command()
@general.try_bot_perms
async def war(ctx, member: discord.Member, *, reason: str = None):
    msg = f'{member.mention} has been warred :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)

@bot.command()
@general.has_perms('kick_members')
@general.try_bot_perms
async def kick(ctx, member: discord.Member, *, reason: str = None):
    await member.kick(reason=reason)

@bot.command()
@general.has_perms('ban_members')
@general.try_bot_perms
async def ban(ctx, member: discord.Member, *, reason: str = None):
    await member.ban(reason=reason, delete_message_seconds=0)

@bot.command()
@general.work_in_progress
@general.has_perms('moderate_members')
@general.try_bot_perms
async def check_inactive(ctx):
    ...

@bot.command()
@general.has_perms('moderate_members')
@general.can_moderate_member
@general.try_bot_perms
async def mute(ctx, member: discord.Member, duration: str = None, *, reason: str = None):
    await moderation.mute(ctx, member, duration, reason)

@bot.command()
@general.has_perms('moderate_members')
@general.can_moderate_member
@general.try_bot_perms
async def unmute(ctx, member: discord.Member, *, reason: str = None):
    await moderation.unmute(ctx, member, reason)

@bot.command()
@general.has_perms('moderate_members')
@general.try_bot_perms
async def warn(ctx, member: discord.Member, *, reason: str = None):
    await moderation.warn(ctx, member, reason)

@bot.command()
@general.try_bot_perms
async def warns(ctx, member: discord.Member):
    if member.guild.get_role(config.roles['warn_1']) in member.roles:
        await ctx.send(f"this guy has 1 warn :yellow_circle:")
    elif member.guild.get_role(config.roles['warn_2']) in member.roles:
        await ctx.send(f"this guy has 2 warns :orange_circle:")
    elif member.guild.get_role(config.roles['warn_3']) in member.roles:
        await ctx.send(f"this guy has 3 warns :red_circle:\n-# next warn will ban them btw")
    else:
        await ctx.send(f"this guy doesn't have warns they're an outstanding citizen :white_check_mark:")

@bot.command()
@general.has_perms('moderate_members')
@general.can_moderate_member
@general.try_bot_perms
async def clear_warns(ctx, member: discord.Member):
    await member.timeout(None)
    await general.remove_role(member, general.config.roles['warn_1'])
    await general.remove_role(member, general.config.roles['warn_2'])
    await general.remove_role(member, general.config.roles['warn_3'])
    await ctx.send(f"cleared all warns :white_check_mark:")

@bot.command()
@general.has_perms('owner')
@general.try_bot_perms
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(config.message("channel_lock"))

@bot.command()
@general.has_perms('owner')
@general.try_bot_perms
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send(config.message("channel_unlock"))


@bot.command()
@general.has_perms('owner')
@general.try_bot_perms
async def r(
    ctx,
    start_id: int,
    end_id: int
):
    channel = ctx.channel
    msg: discord.Message = ctx.message
    await msg.add_reaction('✅')
    try:
        start_message = await channel.fetch_message(start_id)
        end_message = await channel.fetch_message(end_id)
    except discord.NotFound:
        return await ctx.send(
            "one of the message ids wasn't found, make sure u doin the right thing",
            delete_after=5
        )
    except discord.HTTPException as e:
        return await ctx.send(
            f"unable to fetch msgs: {e}",
            delete_after=5
        )

    # Ensure start_message is chronologically before or at the same time as end_message
    if start_message.created_at > end_message.created_at:
        start_message, end_message = end_message, start_message

    messages_to_delete = []
    async for message in channel.history(
        limit=None,
        before=end_message.created_at,
        after=start_message.created_at,
    ):
        messages_to_delete.append(message)

    # Add the start and end messages themselves if they weren't caught by before/after
    if start_message not in messages_to_delete:
        messages_to_delete.append(start_message)
    if end_message not in messages_to_delete:
        messages_to_delete.append(end_message)

    # Sort messages by creation time to ensure consistent deletion order
    messages_to_delete.sort(key=lambda m: m.created_at)

    if not messages_to_delete:
        return await ctx.send(
            "there are no messages between those ids",
            delete_after=5
        )

    await channel.delete_messages(messages_to_delete)
    await ctx.message.delete()
    return await ctx.send(
        f"{len(messages_to_delete)} messages deleted :white_check_mark:"
    )


import subprocess
@bot.command()
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
@general.work_in_progress
async def br(ctx):
    return await ctx.reply('sry fam ts command no workie and im too lazy to fix it so its cancelled for now')



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