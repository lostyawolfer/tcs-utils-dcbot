import re
import discord
from typing import Optional


def parse_challenge_role(role: discord.Role) -> Optional[dict]:
    """Parse a challenge role and extract information."""
    if not role.name.startswith('🏆'):
        return None

    # Pattern: 🏆<tier_emoji> <name> /+<points>/
    pattern = r'^🏆([🟢⭐☄️])\s+(.+?)\s+/\+(\d+)/$'
    match = re.match(pattern, role.name)

    if not match:
        return None

    tier_emoji, name, points = match.groups()

    return {
        'tier_emoji': tier_emoji,
        'name': name,
        'points': int(points),
        'role_id': role.id
    }


def calculate_points(member: discord.Member) -> tuple[int, list[int]]:
    """Calculate total points and return list of challenge role IDs."""
    total = 0
    challenge_roles = []

    for role in member.roles:
        role_info = parse_challenge_role(role)
        if role_info:
            total += role_info['points']
            challenge_roles.append((role_info['points'], role.id))

    # Sort by points (descending)
    challenge_roles.sort(reverse=True, key=lambda x: x[0])

    return total, [role_id for _, role_id in challenge_roles]


def get_leaderboard(guild: discord.Guild) -> list[tuple[discord.Member, int]]:
    """Get leaderboard sorted by points."""
    leaderboard = []

    for member in guild.members:
        if member.bot:
            continue
        total_points, _ = calculate_points(member)
        if total_points > 0:
            leaderboard.append((member, total_points))

    leaderboard.sort(reverse=True, key=lambda x: x[1])
    return leaderboard


async def update_leaderboard_message(bot, guild: discord.Guild):
    """Update the leaderboard message in the leaderboard channel."""
    from modules import config

    channel = guild.get_channel(config.channels['leaderboard'])
    if not channel:
        return

    leaderboard = get_leaderboard(guild)
    top_5 = leaderboard[:5]

    lines = ['# the point leaderboard']
    for i, (member, points) in enumerate(top_5, 1):
        # Add extra space for single digit points
        pts_str = f' {points}' if points < 10 else str(points)
        lines.append(f'{i}. `{pts_str} pts` {member.mention}')

    message_text = '\n'.join(lines)

    # Find existing bot message or create new one
    bot_message = None
    async for msg in channel.history(limit=10):
        if msg.author == bot.user:
            bot_message = msg
            break

    if bot_message:
        await bot_message.edit(content=message_text, allowed_mentions=discord.AllowedMentions.none())
    else:
        await channel.send(message_text, allowed_mentions=discord.AllowedMentions.none())