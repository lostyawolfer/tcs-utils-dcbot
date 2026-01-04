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

    if not leaderboard:
        return []

    current_rank = 1
    previous_points = leaderboard[0][1]  # Start with the points of the very first member

    # Process the first member
    ranked_entries.append((current_rank, previous_points, [leaderboard[0][0]]))

    # Process the rest of the members
    for i in range(1, len(leaderboard)):
        member, points = leaderboard[i]

        if points < previous_points:
            # Points decreased, so increment rank for a new unique score
            current_rank = i + 1
            ranked_entries.append((current_rank, points, [member]))
        else:  # Tie with the previous entry's points
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

    lines = ['# THE LEADERBOARD', '** **']  # Title and empty line

    # Iterate through the ranked leaderboard
    # Use an explicit counter for unique ranks displayed
    unique_ranks_displayed = 0
    for rank_entry in ranked_leaderboard:
        if unique_ranks_displayed >= 10:  # Limit to top 10 unique ranks
            break

        rank, points, members = rank_entry

        # Sort members in a tie alphabetically for consistent display
        members.sort(key=lambda m: m.display_name.lower())

        members_mentions = ' '.join([m.mention for m in members])
        pts_str = f' {points}' if points < 10 else str(points)

        # Apply special formatting for top 3
        if rank == 1:
            lines.append(f'# {rank}. `{pts_str} pts` {members_mentions}')
        elif rank == 2:
            lines.append(f'## {rank}. `{pts_str} pts` {members_mentions}')
        elif rank == 3:
            lines.append(f'### {rank}. `{pts_str} pts` {members_mentions}')
        else:
            lines.append(f'{rank}. `{pts_str} pts` {members_mentions}')

        unique_ranks_displayed += 1  # Only increment for a new unique rank

    if len(lines) <= 2:  # If only title and empty line, means no one on leaderboard
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