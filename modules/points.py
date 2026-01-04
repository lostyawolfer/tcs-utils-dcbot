import re
import discord
from typing import Optional, List, Tuple
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
    current_rank_value = 0  # This will track the actual rank number to assign
    previous_points = -1  # Sentinel value, assuming points are non-negative

    for i, (member, points) in enumerate(leaderboard):
        # Determine the rank for the current points
        if points < previous_points or previous_points == -1:
            current_rank_value = i + 1  # New rank
            # Ensure it's appended as a new entry with its own list of members
            ranked_entries.append((current_rank_value, points, [member]))
        else:  # Tie with the previous entry
            # Append member to the last entry's list of members
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

    lines = ['# THE LEADERBOARD', '** **']  # Updated heading

    # Iterate through the top 10 unique ranks
    for rank_idx, (rank, points, members) in enumerate(ranked_leaderboard):
        if rank_idx >= 10:  # Limit to top 10 unique ranks
            break

        # Sort members in a tie alphabetically by display name for consistent display
        members.sort(key=lambda m: m.display_name.lower())

        # Combine all tied members into a single string for this rank
        member_mentions = ' '.join([m.mention for m in members])
        pts_str = f' {points}' if points < 10 else str(points)  # Add space for single digit

        # Apply heading markdown based on rank
        if rank == 1:
            lines.append(f'# {rank}. `{pts_str} pts` {member_mentions}')
        elif rank == 2:
            lines.append(f'## {rank}. `{pts_str} pts` {member_mentions}')
        elif rank == 3:
            lines.append(f'### {rank}. `{pts_str} pts` {member_mentions}')
        else:
            lines.append(f'{rank}. `{pts_str} pts` {member_mentions}')

    if not lines:  # This condition might need adjustment if initial headings are always present
        lines.append('no one on the leaderboard yet!')
    elif len(lines) == 2 and not ranked_leaderboard:  # If only headers and no entries
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