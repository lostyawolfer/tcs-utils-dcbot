import re
import discord
from typing import Optional, List, Tuple, Dict
from collections import defaultdict


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


def calculate_points(member: discord.Member) -> tuple[int, List[int]]:
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


def get_leaderboard(guild: discord.Guild) -> List[Tuple[discord.Member, int]]:
    """Get leaderboard sorted by points."""
    leaderboard = []

    for member in guild.members:
        if member.bot:
            continue
        total_points, _ = calculate_points(member)
        if total_points > 0:
            leaderboard.append((member, total_points))

    # Sort primarily by points (descending), then by member ID for consistent tie-breaking
    leaderboard.sort(key=lambda x: (-x[1], x[0].id))
    return leaderboard


def get_ranked_leaderboard(guild: discord.Guild) -> List[Tuple[int, int, List[discord.Member]]]:
    """
    Get leaderboard with ranks, handling ties.
    Returns: A list of tuples (rank, points, [members_with_these_points])
    """
    leaderboard = get_leaderboard(guild)

    ranked_entries: List[Tuple[int, int, List[discord.Member]]] = []
    current_rank = 0
    previous_points = -1  # Sentinel value

    for i, (member, points) in enumerate(leaderboard):
        if points < previous_points or previous_points == -1:
            current_rank = i + 1
            ranked_entries.append((current_rank, points, [member]))
        else:  # Tie
            ranked_entries[-1][2].append(member)
        previous_points = points

    return ranked_entries


async def update_leaderboard_message(bot, guild: discord.Guild):
    """Update the leaderboard message in the leaderboard channel."""
    from modules import config

    channel = guild.get_channel(config.channels['leaderboard'])
    if not channel:
        return

    ranked_leaderboard = get_ranked_leaderboard(guild)

    lines = ['# the point leaderboard']

    displayed_members_count = 0
    for rank, points, members in ranked_leaderboard:
        if displayed_members_count >= 5:  # Limit to top 5 ranked positions
            break

        # Sort members in a tie alphabetically for consistent display
        members.sort(key=lambda m: m.display_name.lower())

        for i, member in enumerate(members):
            if displayed_members_count >= 5:  # Ensure we don't display more than 5 total members
                break

            pts_str = f' {points}' if points < 10 else str(points)

            if i == 0:  # First member in a tie gets the rank number
                lines.append(f'{rank}. `{pts_str} pts` {member.mention}')
            else:  # Subsequent members in a tie are indented
                lines.append(f'  - `{pts_str} pts` {member.mention}')
            displayed_members_count += 1

    if not lines:
        lines.append('no one on the leaderboard yet!')

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