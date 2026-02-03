import discord
from discord.ui import View, Select
from modules.points import parse_challenge_role
from modules.role_management import RoleSession
from modules import config

WARDROBE_CHANNEL_ID = 1468068634680229979
WARDROBE_CUSTOM_ID = "wardrobe:open"
WARDROBE_MESSAGE_TEXT = (
    "# <:badge_placeholder:1454599839189962783> **badge wardrobe**\n"
    "choose the badge you wish to display near your name!"
)

# -------------------------
# helpers
# -------------------------

def badge_emoji_for_name(guild: discord.Guild, name: str):
    clean = (
        name.lower()
        .replace("'", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
        .replace(" ", "_")
    )
    return discord.utils.get(guild.emojis, name=f"badge_{clean}")


def get_owned_badge_roles(member: discord.Member):
    guild = member.guild
    roles_by_name = {r.name: r for r in guild.roles}

    owned_badges = set()
    all_badges = set()

    for role in guild.roles:
        info = parse_challenge_role(role)
        if not info:
            continue

        badge_name = f"👁 {info['name']}"
        badge = roles_by_name.get(badge_name)
        if badge:
            all_badges.add(badge)
            if role in member.roles:
                owned_badges.add(badge)

    # exceptions
    exceptions = {
        "👑⭐ beat all base challenges": "👁 challenge completion star",
        "👑☄️ beat all ultimate challenges": "👁 pure challenge completion star",
    }

    for challenge_name, badge_name in exceptions.items():
        c = roles_by_name.get(challenge_name)
        b = roles_by_name.get(badge_name)
        if b:
            all_badges.add(b)
            if c and c in member.roles:
                owned_badges.add(b)

    return owned_badges, all_badges


# -------------------------
# views
# -------------------------

class WardrobeOpenView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="open wardrobe",
        style=discord.ButtonStyle.secondary, # type: ignore
        emoji="🥇",
        custom_id=WARDROBE_CUSTOM_ID,
    )
    async def open(self, interaction: discord.Interaction, _):
        member = interaction.user
        owned, _ = get_owned_badge_roles(member)

        if not owned:
            return await interaction.response.send_message( # type: ignore
                "you don’t own any badges yet - complete challenges to unlock them!",
                ephemeral=True,
            )

        return await interaction.response.send_message( # type: ignore
            "pick a badge to display:",
            view=WardrobeSelectView(member),
            ephemeral=True,
        )


class WardrobeSelectView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self.member = member

        owned, _ = get_owned_badge_roles(member)

        options = [
            discord.SelectOption(
                label="none",
                description="remove displayed badge",
                value="none",
                emoji="❌",
            )
        ]

        for badge in sorted(owned, key=lambda r: r.position, reverse=True):
            emoji = badge_emoji_for_name(member.guild, badge.name.replace("👁 ", ""))
            options.append(
                discord.SelectOption(
                    label=badge.name.replace("👁 ", ""),
                    value=str(badge.id),
                    emoji=emoji,
                )
            )

        self.add_item(WardrobeSelect(options=options))


class WardrobeSelect(Select):
    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        _, all_badges = get_owned_badge_roles(member)

        choice = self.values[0]

        async with RoleSession(member) as rs:
            for badge in all_badges:
                rs.remove(badge.id)

            if choice != "none":
                rs.add(int(choice))

        if choice == "none":
            text = "badge removed ✅"
        else:
            text = "done, badge updated, go show it off ✨"

        await interaction.response.edit_message( # type: ignore
            content=text,
            view=None,
        )


# -------------------------
# setup
# -------------------------

async def ensure_wardrobe_message(bot: discord.Client):
    guild = bot.get_guild(config.TARGET_GUILD)
    channel = guild.get_channel(WARDROBE_CHANNEL_ID)
    if not channel:
        return

    async for msg in channel.history(limit=25):
        if msg.author == bot.user and msg.components:
            for row in msg.components:
                for c in row.children:
                    if getattr(c, "custom_id", None) == WARDROBE_CUSTOM_ID:
                        return

    await channel.send(
        WARDROBE_MESSAGE_TEXT,
        view=WardrobeOpenView(),
        allowed_mentions=discord.AllowedMentions.none(),
    )