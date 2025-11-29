import discord
from discord.ext import commands
import moderation
import availability_vc
import general
import config

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    await general.set_status(bot, 'startup')
    for guild in bot.guilds:
        if config.check_guild(guild.id):
            await bot.change_presence(status=discord.Status.idle)
            await general.set_status(bot, 'checking members')
            #member_n = 0
            for member in guild.members:
                #member_n += 1
                if not member.bot:
                    await availability_vc.pure_availability_check(bot, member)
                    await availability_vc.voice_check(bot, member)
            await bot.change_presence(status=discord.Status.online)
            await general.update_status(bot)
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
        for role in removed_roles:
            if role.id == config.roles['mod']:
                await general.send(bot, config.message('demotion', mention=after.mention))
                await general.send(bot, config.message('demotion_goodbye', mention=after.mention), 'mod_chat')
            if role.id == config.roles['leader']:
                await general.send(bot, config.message('leader_removed', mention=after.mention))
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



@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if '<#1426974154556702720>' in message.content:
        await message.channel.send(f'link: **https://www.roblox.com/share?code=1141897d2bd9a14e955091d8a4061ee5&type=Server**', suppress_embeds=True)
    await bot.process_commands(message)

@bot.command()
async def test(ctx):
    await ctx.send('test pass')

@bot.command()
@general.has_perms('kick_members')
@general.try_perm
async def kick(ctx, member: discord.Member, *, reason: str = None):
    await member.kick(reason=reason)

@bot.command()
@general.has_perms('ban_members')
@general.try_perm
async def ban(ctx, member: discord.Member, *, reason: str = None):
    await member.ban(reason=reason, delete_message_days=0, delete_message_seconds=0)

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
@general.has_perms('manage_channels')
@general.try_perm
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(config.message("channel_lock"))

@bot.command()
@general.has_perms('manage_channels')
@general.try_perm
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send(config.message("channel_unlock"))









@bot.command()
async def br(ctx, *args):
    # if not ctx.guild.get_role(ROLES['mod']) not in ctx.author.roles:
    #     return await ctx.send(message("nuh_uh"))
    parsed_args = list(args)
    if len(parsed_args) == 0:
        return await ctx.send(
            'usage `.br <challenge> [best?] <route> <death-floor> <death-door> [flag][participants] -- <reason>`\n'
            'format `.br <tcs/gor/pdo> [b] bh[ro]m[-l] <b/h/r/o/m> (int) [-l @leader] [-d @dead_member] [-x @disconnected_member] [@normal_member] ... -- (str)`\n'
            'death-door argument can also represent death meters in outdoors if death-floor is \'o\'\n'
            '-l at the end of route means long rooms and only works if r is included. long rooms means up to a-1000, short rooms means up to a-200'
        )

    run_type = parsed_args.pop(0).lower()
    if run_type not in config.emoji:
        return await ctx.send(
            f'invalid challenge `{run_type}`'
        )

    new_best = False
    if len(parsed_args) >= 1 and parsed_args[0] == 'b':
        new_best = True
        parsed_args.pop(0)

    if len(parsed_args) < 3:  # minimum route, death-floor, death-door
        return await ctx.send('wrong usage :wilted_rose:')

    route = parsed_args[0]
    death_floor = parsed_args[1]
    try:
        death_time = int(parsed_args[2])
    except ValueError:
        await ctx.send(
            'wrong death door it has to be an integer :wilted_rose:'
        )
        return None

    death_point = (death_floor, death_time)

    # Find the separator for reason
    try:
        reason_separator_index = parsed_args.index('--', 3)
    except ValueError:
        return await ctx.send(
            'pls tell me the run failure reason after `--`'
        )

    # Extract participant arguments and reason
    participant_args = parsed_args[3:reason_separator_index]
    reason = ' '.join(parsed_args[reason_separator_index + 1 :])

    if not reason:
        return await ctx.send('how tf did u fail? tell me! after `--` at the end of the command')

    from best_runs import RunMember, RunDetails
    participants: list[RunMember] = []

    # Helper to create a RunMember from a discord.Member
    async def create_run_member(member: discord.Member):
        return RunMember(
            member=member,
            is_leader=current_member_flags['is_leader'],
            is_dead=current_member_flags['is_dead'],
            is_disconnected=current_member_flags['is_disconnected'],
        )

    current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}
    # Process participant arguments
    for arg in participant_args:
        if arg == '-l':
            current_member_flags['is_leader'] = True
        if arg == '-d':
            current_member_flags['is_dead'] = True
        if arg == '-x':
            current_member_flags['is_disconnected'] = True
        if arg not in ['-x', '-d', '-l']:
            try:
                # Resolve member from mention (e.g., <@123456789>)
                member = await commands.MemberConverter().convert(ctx, arg)
                participants.append(await create_run_member(member))
                current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}
            except commands.MemberNotFound:
                await ctx.send(f'Could not find member: `{arg}`')
            finally:
                # Reset flags after adding a member or if it's not a flag
                current_member_flags = {'is_leader': False, 'is_dead': False, 'is_disconnected': False}

    run_details = RunDetails(
        run_type=run_type,
        route=route,
        death_point=death_point,
        reason=reason,
        participants=participants,
        is_new_best=new_best,
    )
    return await ctx.send(run_details.message_text)


if __name__ == '__main__':
    bot.run(config.TOKEN)