import datetime
import discord
from discord.ext import commands, tasks
import moderation
import availability_vc
import general
import config
from saves import create_save, disband_save

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)


@tasks.loop(seconds=1)
async def status_updater_loop():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if 2 <= now_utc.second <= 3:
        await general.update_status(bot)

@bot.event
async def on_ready():
    await general.set_status(bot, 'starting up...', status=discord.Status.idle)
    for guild in bot.guilds:
        if config.check_guild(guild.id):
            await general.update_status_checking(bot, 0)
            total_members = guild.member_count
            member_n = 0
            for member in guild.members:
                member_n += 1
                percent = round(member_n * 100 / total_members)
                if not member.bot:
                    await availability_vc.pure_availability_check(bot, member)
                    await availability_vc.voice_check(bot, member)
                    for role in config.roles['role_check']:
                        await general.add_role(member, role)
                    for role in member.roles:
                        if role.id in config.roles['category:badges']['other']:
                            await general.remove_role(member, config.roles['category:badges']['none'])
                            break
                        await general.add_role(member, config.roles['category:badges']['none'])
                    for role in member.roles:
                        if role.id in config.roles['category:misc']['other']:
                            await general.remove_role(member, config.roles['category:misc']['none'])
                            break
                        await general.add_role(member, config.roles['category:misc']['none'])
                await general.update_status_checking(bot, percent)
            await general.update_status(bot)
            status_updater_loop.start()
            break

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

            if role.id in config.roles['category:badges']['other']:
                for badge in after_roles:
                    if badge.id in config.roles['category:badges']['other']:
                        break
                    await general.add_role(after, config.roles['category:badges']['none'])
            if role.id in config.roles['category:misc']['other']:
                for badge in after_roles:
                    if badge.id in config.roles['category:misc']['other']:
                        break
                    await general.add_role(after, config.roles['category:misc']['none'])

    if before.nick != after.nick:
        old = before.nick if before.nick else before.name
        new = after.nick if after.nick else after.name
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
        await general.send(bot, '-# hey there! check out <#1426974985402187776> <#1432401559672848507> <#1434653852367585300>')
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

@bot.command()
async def test(ctx):
    await ctx.send('test pass')

@general.try_perm
@bot.command()
async def save(ctx, *members: discord.Member):
    if not members:
        return await ctx.send("usage: `.save @member1 @member2 ...`")
    return await create_save(ctx, list(members))

@bot.command()
async def disband(ctx):
    await disband_save(ctx)

@bot.command()
@general.is_owner
@general.try_perm
async def check_members(ctx):
    await ctx.send('aight')
    await bot.change_presence(status=discord.Status('idle'))
    await general.update_status_checking(bot, 0)
    total_members = ctx.guild.member_count
    member_n = 0
    for member in ctx.guild.members:
        member_n += 1
        percent = round(member_n * 100 / total_members)
        if not member.bot:
            await availability_vc.pure_availability_check(bot, member)
            await availability_vc.voice_check(bot, member)
            for role in config.roles['role_check']:
                await general.add_role(member, role)
            for role in member.roles:
                if role.id in config.roles['category:badges']['other']:
                    await general.remove_role(member, config.roles['category:badges']['none'])
                    break
                await general.add_role(member, config.roles['category:badges']['none'])
            for role in member.roles:
                if role.id in config.roles['category:misc']['other']:
                    await general.remove_role(member, config.roles['category:misc']['none'])
                    break
                await general.add_role(member, config.roles['category:misc']['none'])
        await general.update_status_checking(bot, percent)
    await bot.change_presence(status=discord.Status('online'))
    await general.update_status(bot)

@bot.command()
@general.try_perm
async def van(ctx, member: discord.Member, *, reason: str = None):
    msg = f'{member.mention} has been vanned :white_check_mark:'
    if reason:
        msg += f'\nreason: {reason}'
    await ctx.send(msg)

@bot.command()
@general.has_perms('kick_members')
@general.try_perm
async def kick(ctx, member: discord.Member, *, reason: str = None):
    await member.kick(reason=reason)

@bot.command()
@general.has_perms('ban_members')
@general.try_perm
async def ban(ctx, member: discord.Member, *, reason: str = None):
    await member.ban(reason=reason, delete_message_seconds=0)

@bot.command()
@general.try_perm
async def check_newbies(ctx):
    author_perms = ctx.author.guild_permissions
    if not getattr(author_perms, 'moderate_members', False):
        return await ctx.send(config.message("nuh_uh"))
    await bot.change_presence(status=discord.Status('idle'))
    await general.update_status_checking(bot, 0)
    total_members = ctx.guild.member_count
    member_n = 0
    for member in ctx.guild.members:
        member_n += 1
        percent = round(member_n * 100 / total_members)
        if not member.bot:
            if ctx.guild.get_role(config.roles['newbie']) in member.roles:
                if member.joined_at:
                    now = datetime.datetime.now(member.joined_at.tzinfo)
                    time_since_join = now - member.joined_at
                    days = time_since_join.days
                    if days > 7:
                        await general.remove_role(member, config.roles['newbie'])
        await general.update_status_checking(bot, percent)
    await bot.change_presence(status=discord.Status('online'))
    return await general.update_status(bot)

@bot.command()
@general.try_perm
async def check_inactive(ctx):
    author_perms = ctx.author.guild_permissions
    if not getattr(author_perms, 'moderate_members', False):
        ...

@bot.command()
@general.has_perms('moderate_members')
@general.try_perm
async def mute(ctx, member: discord.Member, duration: str, *, reason: str = None):
    await moderation.mute(ctx, member, duration, reason)

@bot.command()
@general.has_perms('moderate_members')
@general.try_perm
async def unmute(ctx, member: discord.Member, *, reason: str = None):
    await moderation.unmute(ctx, member, reason)

@bot.command()
@general.has_perms('moderate_members')
@general.try_perm
async def warn(ctx, member: discord.Member, *, reason: str = None):
    await moderation.warn(ctx, member, reason)

@bot.command()
@general.try_perm
async def warns(ctx, member: discord.Member):
    if member.guild.get_role(config.roles['warn_1']) in member.roles:
        await ctx.send(f"this guy has 1 warn :yellow_circle:")
    elif member.guild.get_role(config.roles['warn_2']) in member.roles:
        await ctx.send(f"this guy has 2 warns :orange_circle:")
    elif member.guild.get_role(config.roles['warn_3']) in member.roles:
        await ctx.send(f"this guy has 3 warns :red_circle:\nnext warn will ban them btw")
    else:
        await ctx.send(f"this guy doesn't have warns they're an outstanding citizen :white_check_mark:")

@bot.command()
@general.has_perms('moderate_members')
@general.try_perm
async def clear_warns(ctx, member: discord.Member):
    await member.timeout(None)
    await general.remove_role(member, general.config.roles['warn_1'])
    await general.remove_role(member, general.config.roles['warn_2'])
    await general.remove_role(member, general.config.roles['warn_3'])
    await ctx.send(f"cleared all warns :white_check_mark:")

@bot.command()
@general.is_owner
@general.try_perm
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(config.message("channel_lock"))

@bot.command()
@general.is_owner
@general.try_perm
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send(config.message("channel_unlock"))


@general.is_owner
@general.try_perm
@bot.command()
async def r(
    ctx,
    start_id: int,
    end_id: int
):
    channel = ctx.channel

    await ctx.message.delete()  # Delete the command invocation message

    try:
        start_message = await channel.fetch_message(start_id)
        end_message = await channel.fetch_message(end_id)
    except discord.NotFound:
        return await ctx.send(
            "One or both of the message IDs were not found.",
            delete_after=5
        )
    except discord.HTTPException as e:
        return await ctx.send(
            f"An error occurred while fetching messages: {e}",
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
    return await ctx.send(
        f"{len(messages_to_delete)} messages deleted :white_check_mark:",
        delete_after=5
    )



@bot.command()
async def br(ctx):
    await ctx.reply('sry fam ts command no workie and im too lazy to fix it so its cancelled for now')



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