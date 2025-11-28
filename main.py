import datetime
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks
from config import message, check_guild, TARGET_GUILD, ROLES, CHANNELS, TOKEN, EMOJI

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



async def count_people_in_vc(vc: str) -> int:
    guild = bot.get_guild(TARGET_GUILD)
    channel = guild.get_channel(CHANNELS[vc])
    res = len(channel.members)
    return res

async def check_voice_state(member: discord.Member) -> None:
    guild = member.guild
    if not check_guild(guild.id):
        return

    vc = guild.get_channel(CHANNELS['vc'])
    vc2 = guild.get_channel(CHANNELS['vc2'])
    if not vc:
        return

    if member.voice and member.voice.channel == vc:
        if not has_role(member, ROLES['in_vc']):
            await send(message('join_vc', name=member.display_name, count=await count_people_in_vc('vc')))

        if has_role(member, ROLES['leader']):
            await add_role(member, ROLES['in_vc_leader'])
        await add_role(member, ROLES['in_vc'])
        await remove_role(member, ROLES['not_in_vc'])

    else:
        if has_role(member, ROLES['in_vc']):
            await send(message('leave_vc', name=member.display_name, count=await count_people_in_vc('vc')))
        await remove_role(member, ROLES['in_vc'])
        await remove_role(member, ROLES['in_vc_leader'])
        await add_role(member, ROLES['not_in_vc'])

    if member.voice and member.voice.channel == vc2:
        if not has_role(member, ROLES['in_vc_2']):
            await send(message('join_vc_2', name=member.display_name, count=await count_people_in_vc('vc2')))

        if has_role(member, ROLES['leader']):
            await add_role(member, ROLES['in_vc_2_leader'])
        await add_role(member, ROLES['in_vc_2'])
        await remove_role(member, ROLES['not_in_vc_2'])

    else:
        if has_role(member, ROLES['in_vc_2']):
            await send(message('leave_vc_2', name=member.display_name, count=await count_people_in_vc('vc2')))
        await remove_role(member, ROLES['in_vc_2'])
        await remove_role(member, ROLES['in_vc_2_leader'])
        await add_role(member, ROLES['not_in_vc_2'])


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



def get_status() -> str:
    vc = count_people_in_vc('vc')
    vc2 = count_people_in_vc('vc2')
    av = count_available_people()
    return f'{av} available / {vc} in vc'
@tasks.loop(seconds=3) # Updates every 60 seconds
async def change_status():
    status_message = get_status()
    # if not count_people_in_vc('vc') and not count_people_in_vc('vc2'):
    #     await bot.change_presence(status=discord.Status('Idle'))
    # else:
    #     await bot.change_presence(status=discord.Status('Online'))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))
    print(f"Status updated to: {status_message}")


@bot.event
async def on_ready():
    if not change_status.is_running():
        change_status.start()
    for guild in bot.guilds:
        if check_guild(guild.id):
            status_message = await guild.get_channel(CHANNELS['chat']).send('bot restarted\n-# ...')
            await status_message.edit(content=f'bot restarted\n-# *preparing*')
            member_n = 0
            for member in guild.members:
                member_n += 1
                await status_message.edit(
                    content=f'bot restarted\n-# *checking member {member_n}/{guild.member_count}* …')
                if not member.bot:
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

    if member.bot:
        return

    vc = guild.get_channel(CHANNELS['vc'])
    vc2 = guild.get_channel(CHANNELS['vc2'])
    if not vc or not vc2:
        return

    await check_voice_state(member)

@bot.event
async def on_raw_reaction_add(payload):
    if not check_guild(payload.guild_id):
        return
    if payload.member and payload.member.bot:
        return
    if payload.message_id == CHANNELS['availability_message']:
        emoji_id = payload.emoji.id
        if emoji_id == CHANNELS['availability_reaction']:
            await add_availability(bot.get_guild(payload.guild_id).get_member(payload.user_id))


@bot.event
async def on_raw_reaction_remove(payload):
    if not check_guild(payload.guild_id):
        return
    if payload.member and payload.member.bot:
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
#@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:
        return await ctx.send(message("nuh_uh"))
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.kick_members:
        return await ctx.send(message("nuh_uh"))

    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to kick {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error kicking {member.display_name} (ID: {member.id}): {e}")

@bot.command()
#@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:  # Prevent bot from kicking itself
        return await ctx.send(message("nuh_uh"))
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.ban_members:
        return await ctx.send(message("nuh_uh"))

    try:
        await member.ban(reason=reason, delete_message_days=0, delete_message_seconds=0)
    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to ban {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error banning {member.display_name} (ID: {member.id}): {e}")

@bot.command()
#@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:
        return await ctx.send(message("nuh_uh"))
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(message("nuh_uh"))

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
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to timeout {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error muting {member.display_name} (ID: {member.id}): {e}")

@bot.command()
#@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member, *, reason: str = None):
    if not member.is_timed_out():
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(message("nuh_uh"))

    try:
        await member.timeout(None, reason=reason) # Setting duration to None removes timeout
        await ctx.send(f"unmuted :white_check_mark:")
        print(f"Unmuted {member.display_name} (ID: {member.id}) by {ctx.author.display_name} for: {reason}")
    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to unmute {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error unmuting {member.display_name} (ID: {member.id}): {e}")



@bot.command()
async def warn(ctx, member: discord.Member, *, reason: str = None):
    if member == ctx.author:
        return await ctx.send(message("nuh_uh"))
    if member == ctx.guild.me:
        return await ctx.send(message("nuh_uh"))
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(message("nuh_uh"))

    try:
        if member.guild.get_role(ROLES['warn_1']) in member.roles:
            timeout_duration = datetime.timedelta(days=3)
            await member.timeout(timeout_duration, reason=reason)
            await add_role(member, ROLES['warn_2'])
            await remove_role(member, ROLES['warn_1'])
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 2/3\nthey're muted for 3 days")

        elif member.guild.get_role(ROLES['warn_2']) in member.roles:
            timeout_duration = datetime.timedelta(days=7)
            await member.timeout(timeout_duration, reason=reason)
            await add_role(member, ROLES['warn_3'])
            await remove_role(member, ROLES['warn_2'])
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 3/3\nthey're muted for 7 days\nnext warn will ban them btw")

        elif member.guild.get_role(ROLES['warn_3']) in member.roles:
            await member.ban()

        else:
            timeout_duration = datetime.timedelta(days=1)
            await add_role(member, ROLES['warn_1'])
            await member.timeout(timeout_duration, reason=reason)
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 1/3\nthey're muted for 1 day")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error warning {member.display_name} (ID: {member.id}): {e}")

@bot.command()
async def warns(ctx, member: discord.Member):
    try:
        if member.guild.get_role(ROLES['warn_1']) in member.roles:
            await ctx.send(f"this guy has 1 warn :yellow_circle:")

        elif member.guild.get_role(ROLES['warn_2']) in member.roles:
            await ctx.send(f"this guy has 2 warns :orange_circle:")

        elif member.guild.get_role(ROLES['warn_3']) in member.roles:
            await ctx.send(f"this guy has 3 warns :red_circle:\nnext warn will ban them btw")

        else:
            await ctx.send(f"this guy doesn't have warns they're an outstanding citizen :white_check_mark:")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error checking warns {member.display_name} (ID: {member.id}): {e}")

@bot.command()
async def clear_warns(ctx, member: discord.Member):
    if not member.is_timed_out():
        return await ctx.send(message("nuh_uh"))
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(message("nuh_uh"))

    try:
        await member.timeout(None)
        await remove_role(member, ROLES['warn_1'])
        await remove_role(member, ROLES['warn_2'])
        await remove_role(member, ROLES['warn_3'])
        await ctx.send(f"cleared all warns :white_check_mark:")
    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to unwarn {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms"))
        print(f"Error unwarning {member.display_name} (ID: {member.id}): {e}")


@bot.command()
async def lock(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(message("nuh_uh"))

    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(message("channel_lock"))

    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms") + '\n' + f'{e}')

@bot.command()
async def unlock(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(message("nuh_uh"))

    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send(message("channel_unlock"))

    except discord.Forbidden:
        await ctx.send(message("bot_doesnt_have_perms"))
    except Exception as e:
        await ctx.send(message("bot_doesnt_have_perms") + '\n' + f'{e}')


@dataclass
class RunMember:
    member: discord.Member
    is_leader: bool = False
    is_dead: bool = False
    is_disconnected: bool = False

    @property
    def display_name(self):
        return self.member.display_name if self.member else '???'


    @property
    def emoji(self):
        emoji = []
        if self.is_leader:
            emoji.append(EMOJI['leader'])
        if self.is_dead:
            emoji.append(EMOJI['death'])
        if self.is_disconnected:
            emoji.append(EMOJI['disconnect'])
        if not emoji:
            emoji.append(EMOJI['blank'])
        return ''.join(emoji)

from dataclasses import dataclass


@dataclass
class RunDetails:
    run_type: str
    route: str
    death_point: tuple[str, int]
    reason: str
    participants: list[RunMember]
    is_new_best: bool = False

    @property
    def max_doors(self) -> int | None:
        if self.route == "bhm":  # backdoor hotel mines
            return 50 + 100 + 100
        elif self.route == "bhom":  # backdoor hotel outdoors mines
            return 50 + 90 + 35 + 50
        elif self.route == "bhrm":  # backdoor hotel rooms hotel mines
            return 50 + 60 + 200 + 33 + 100
        elif self.route == "bhrm-l":  # backdoor hotel rooms hotel mines (long rooms)
            return 50 + 60 + 1000 + 33 + 100
        elif self.route == "bhrom":  # backdoor hotel rooms hotel outdoors mines
            return 50 + 60 + 200 + 23 + 35 + 50
        elif self.route == "bhrom-l":  # backdoor hotel rooms hotel outdoors mines (long rooms)
            return 50 + 60 + 1000 + 23 + 35 + 50
        else:
            return None

    @property
    def progress_doors(self):
        rooms_length = 1000 if "-l" in self.route else 200

        if self.route == "bhm":
            return self.death_point[1] + 50
        elif self.route == "bhom":
            if self.death_point[0] == "b" or self.death_point[0] == "h":
                return self.death_point[1] + 50
            elif self.death_point[0] == "m":
                return self.death_point[1] - 150 + 50 + 90 + 35
            elif self.death_point[0] == "o":
                return self.death_point[1] / 2550 * 35 + 50 + 90
            else:
                return None
        elif self.route in ["bhrm", "bhrm-l"]:
            if (self.death_point[0] == "b" or self.death_point[0] == "h") and self.death_point[1] <= 60:
                return self.death_point[1] + 50
            elif self.death_point[0] == "h" and self.death_point[1] >= 67:
                return self.death_point[1] + 50 + rooms_length
            elif self.death_point[0] == "r":
                return min(self.death_point[1] + 50 + 60, rooms_length + 50 + 60)
            elif self.death_point[0] == "m":
                return self.death_point[1] + 50 + rooms_length - 7
            else:
                return None
        elif self.route in ["bhrom", "bhrom-l"]:
            if (self.death_point[0] == "b" or self.death_point[0] == "h") and self.death_point[1] <= 60:
                return self.death_point[1] + 50
            elif self.death_point[0] == "h" and self.death_point[1] >= 67:
                return self.death_point[1] + 50 + rooms_length
            elif self.death_point[0] == "r":
                return min(self.death_point[1] + 50 + 60, rooms_length + 50 + 60)
            elif self.death_point[0] == "o":
                return self.death_point[1] / 2550 * 35 + 50 + 60 + rooms_length + 23
            elif self.death_point[0] == "m":
                return self.death_point[1] - 150 + 50 + 60 + rooms_length + 23 + 35
            else:
                return None
        else:
            return None

    @property
    def progress_percent(self) -> float:
        if self.max_doors is None or self.progress_doors is None:
            return 0.0  # Handle cases where max_doors or progress_doors is None
        return min(self.progress_doors / self.max_doors * 100, 99.9)

    @property
    def message_text(self) -> str:
        routes = {
            "bhm": ["backdoor", "hotel", "mines"],
            "bhom": ["backdoor", "hotel", "outdoors", "mines"],
            "bhrm": ["backdoor", "hotel", "rooms", "hotel", "mines"],
            "bhrm-l": ["backdoor", "hotel", "rooms", "hotel", "mines"],
            "bhrom": ["backdoor", "hotel", "rooms", "hotel", "outdoors", "mines"],
            "bhrom-l": ["backdoor", "hotel", "rooms", "hotel", "outdoors", "mines"],
        }

        if self.route not in routes:
            return "~~backdoor~~\n~~hotel~~\n~~mines~~"

        stages = routes[self.route]
        current_stage = self.death_point[0]
        current_value = self.death_point[1]

        # Format the current value appropriately
        if current_stage == "r":
            current_display = f"a-{current_value:03d}"
        elif current_stage == "o":
            current_display = f"{current_value}m"
        else:
            current_display = current_value

        # Determine current stage index
        if current_stage == "h" and "rooms" in stages:
            # Routes with rooms: distinguish between first and second hotel
            current_stage_index = 3 if current_value > 67 else 1
        else:
            # Find first occurrence of stage by character
            current_stage_index = next(
                (i for i, s in enumerate(stages) if s[0] == current_stage), -1
            )  # Added default -1

        progress_lines = []
        for i, stage in enumerate(stages):
            if i == current_stage_index:
                progress_lines.append(f"**{stage}** `{current_display}`")
            elif i < current_stage_index:
                progress_lines.append(f"{stage} `complete`")
            else:
                progress_lines.append(f"~~{stage}~~")

        progress = "\n".join(progress_lines)

        sorted_participants = sorted(
            self.participants,
            key=lambda p: (not p.is_leader, p.display_name.lower()),
        )

        participant_lines = []
        for i, p in enumerate(sorted_participants):
            member_mention = p.member.mention if p.member else "@???"
            participant_lines.append(
                f"{i + 1}. {p.emoji}{member_mention} `{p.display_name}`"
            )
        participants_text = (
            "\n".join(participant_lines) if participant_lines else "[no one]"
        )

        return (
            f'# {EMOJI[f'{self.run_type}']} {"*NEW BEST!*" if self.is_new_best else ""} {round(self.progress_percent, 1)}%\n'
            f"-# `{round(self.progress_doors)}/{self.max_doors}`\n"
            f"{progress}\n"
            f"\n"
            f"## PARTICIPANTS\n"
            f"{participants_text}\n"
            f"\n"
            f"run failure reason:\n"
            f"**{self.reason}**"
        )



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
    if run_type not in EMOJI:
        return await ctx.send(
            f'invalid challenge `{run_type}`'
        )

    new_best = False
    if len(parsed_args) >= 1 and parsed_args[0] == 'b':
        new_best = True
        parsed_args.pop(0)

    if len(parsed_args) < 3:  # minimum route, death-floor, death-door
        return await ctx.send('wrong usage fk u :wilted_rose:')

    route = parsed_args[0]
    death_floor = parsed_args[1]
    try:
        death_time = int(parsed_args[2])
    except ValueError:
        await ctx.send(
            'wrong death door fk u it has to be an integer :wilted_rose:'
        )
        return None

    death_point = (death_floor, death_time)

    # Find the separator for reason
    try:
        reason_separator_index = parsed_args.index('--', 3)
    except ValueError:
        return await ctx.send(
            'Please specify the run failure reason after `--`.'
        )

    # Extract participant arguments and reason
    participant_args = parsed_args[3:reason_separator_index]
    reason = ' '.join(parsed_args[reason_separator_index + 1 :])

    if not reason:
        return await ctx.send('Please provide a reason for the run failure.')

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
    bot.run(TOKEN)