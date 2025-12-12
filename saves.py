import discord
import asyncio
import datetime
from discord.ext import commands
import config
from general import add_role, remove_role, send

SAVE_COOLDOWN = {}  # {user_id: datetime.datetime of last save}

SAVE_CATEGORY_NAME = "──╱ saves ╱───────"
SAVE_CHANNEL_TEMPLATE = "💾┃save-{num}"
SAVE_ROLE_TEMPLATE = "💾 save {num}"

async def create_save(ctx, members: list[discord.Member]):
    guild = ctx.guild

    # cooldown abuse protection
    now = datetime.datetime.utcnow()
    user_id = ctx.author.id
    last_use = SAVE_COOLDOWN.get(user_id)

    if last_use:
        diff = (now - last_use).total_seconds()
        if diff < 120:
            if diff < 60:
                return await ctx.send("nuh uh ur using ts too fast wait a bit")
            else:
                await send(ctx.bot, f"<@&{config.roles['mod']}> `{ctx.author.display_name}` is very sus they seem to abuse the save cmd")
    SAVE_COOLDOWN[user_id] = now

    # ensure "saves" category exists
    save_category: discord.CategoryChannel = discord.utils.get(guild.categories, name=SAVE_CATEGORY_NAME)
    if not save_category:
        save_category = await guild.create_category(
            SAVE_CATEGORY_NAME,
            reason="automatically created for save channels",
        )
        await save_category.move(position=2)

    # find next save number
    existing_saves = [
        role for role in guild.roles if role.name.startswith("save ")
    ]
    existing_nums = [
        int(role.name.split()[1])
        for role in existing_saves
        if role.name.split()[1].isdigit()
    ]
    new_num = max(existing_nums, default=0) + 1

    # create role
    save_role = await guild.create_role(
        name=SAVE_ROLE_TEMPLATE.format(num=new_num),
        reason="new save group created",
    )

    # assign role to members
    for m in members:
        await add_role(m, save_role.id)
        # remove misc none if exists
        misc_none = guild.get_role(config.roles['category:misc']['none'])
        if misc_none in m.roles:
            await remove_role(m, misc_none.id)

    # create text channel
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        save_role: discord.PermissionOverwrite(read_messages=True),
    }
    text_channel = await guild.create_text_channel(
        SAVE_CHANNEL_TEMPLATE.format(num=new_num),
        category=save_category,
        overwrites=overwrites,
        reason="private save channel",
    )

    pinned_msg = await text_channel.send(
        f"# hi save group {new_num}\n"
        f"saved run with members {' '.join([m.mention for m in members])}\n"
        f"use this to coordinate or discuss your latest run!\n"
        f"**careful**: this channel is temporary and should be deleted when you are done with the run\n"
        f"additionally pls know that the owner has access to this channel at all times regardless of permissions, it's just a discord thing\n"
        f"**to remove this save, use `.disband` in this channel**\n"
    )
    await pinned_msg.pin()

    return await ctx.send(
        f"created {save_role.mention} with {len(members)} members :white_check_mark:\n"
        f"-# go to channel {text_channel.mention}"
    )


async def disband_save(ctx):
    channel = ctx.channel
    guild = ctx.guild
    if not channel.category or channel.category.name != SAVE_CATEGORY_NAME:
        return await ctx.send("this command only works inside save channels")

    # find related role
    role_name = channel.name.replace("💾┃save-", "💾 save ")
    number = channel.name.replace("💾┃save-", "")
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        return await ctx.send("couldn't find corresponding role for this save, deleting channel anyway")

    members_with_role = [m for m in guild.members if role in m.roles]

    # remove role and re-add misc none if needed
    await send(ctx.bot, f"🗑️ {ctx.author.mention} disbanded the save number {number} {role.mention}")
    for m in members_with_role:
        await remove_role(m, role.id)
        # check if they have any misc role left
        misc_other = any(
            misc in [r.id for r in m.roles]
            for misc in config.roles['category:misc']['other']
        )
        if not misc_other:
            await add_role(m, config.roles['category:misc']['none'])

    try:
        await role.delete(reason="save disbanded")
    except discord.Forbidden:
        ...

    await channel.delete(reason="save disbanded")

    # check if category now has no other channels
    if not channel.category.channels:
        await channel.category.delete(reason="no saves left")

    return None