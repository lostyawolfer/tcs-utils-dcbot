import discord
import config
import datetime
from general import add_role, remove_role



async def mute(ctx, member: discord.Member, duration: str, reason: str = None):
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
        await ctx.send(config.message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to timeout {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(config.message("bot_doesnt_have_perms"))
        print(f"Error muting {member.display_name} (ID: {member.id}): {e}")

async def unmute(ctx, member: discord.Member, reason: str = None):
    if not member.is_timed_out():
        return await ctx.send(config.message("nuh_uh"))
    if not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(config.message("nuh_uh"))

    try:
        await member.timeout(None, reason=reason) # Setting duration to None removes timeout
        await ctx.send(f"unmuted :white_check_mark:")
        print(f"Unmuted {member.display_name} (ID: {member.id}) by {ctx.author.display_name} for: {reason}")
    except discord.Forbidden:
        await ctx.send(config.message("bot_doesnt_have_perms"))
        print(f"Bot lacks permissions to unmute {member.display_name} (ID: {member.id})")
    except Exception as e:
        await ctx.send(config.message("bot_doesnt_have_perms"))
        print(f"Error unmuting {member.display_name} (ID: {member.id}): {e}")




async def warn(ctx, member: discord.Member, reason: str = None):
    try:
        if member.guild.get_role(config.roles['warn_1']) in member.roles:
            timeout_duration = datetime.timedelta(days=3)
            await member.timeout(timeout_duration, reason=reason)
            await add_role(member, config.roles['warn_2'])
            await remove_role(member, config.roles['warn_1'])
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 2/3\nthey're muted for 3 days")

        elif member.guild.get_role(config.roles['warn_2']) in member.roles:
            timeout_duration = datetime.timedelta(days=7)
            await member.timeout(timeout_duration, reason=reason)
            await add_role(member, config.roles['warn_3'])
            await remove_role(member, config.roles['warn_2'])
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 3/3\nthey're muted for 7 days\nnext warn will ban them btw")

        elif member.guild.get_role(config.roles['warn_3']) in member.roles:
            await member.ban()

        else:
            timeout_duration = datetime.timedelta(days=1)
            await add_role(member, config.roles['warn_1'])
            await member.timeout(timeout_duration, reason=reason)
            await ctx.send(f"warned the guy :white_check_mark:\nwarn 1/3\nthey're muted for 1 day")
    except Exception as e:
        await ctx.send(config.message("bot_doesnt_have_perms"))
        print(f"Error warning {member.display_name} (ID: {member.id}): {e}")
