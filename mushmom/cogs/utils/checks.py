"""
Contains command checks

"""
import discord

from discord.ext import commands
from discord import app_commands

from typing import Union

from . import errors


global_commands = (  # commands that will bypass channel check
    'set',
    'set channel',
    'reset',
    'reset channel'
)


async def not_bot(ctx: commands.Context) -> bool:
    """
    Check if author is a bot

    Parameters
    ----------
    ctx: commands.Context

    Returns
    -------
    bool
        whether or not the author is a bot

    """
    if not ctx.author.bot:
        return True

    raise commands.MissingPermissions(['owner'])


async def in_guild_channel(
        ctx: Union[commands.Context, discord.Interaction],
        raise_error: bool = True
) -> bool:
    """
    Checks if message was sent in designated channel.  If no channel
    is set for the guild, all channels will pass

    Commands or cogs in global_commands/cogs will bypass this check

    Parameters
    ----------
    ctx: Union[commands.Context, discord.Interaction]
    raise_error: bool
        whether or not to raise an error when False

    Returns
    -------
    bool
        whether or not message is in an acceptable channel

    """
    if isinstance(ctx, discord.Interaction):
        ctx = await ctx.client.get_context(ctx)

    guild = await ctx.bot.db.get_guild(ctx.guild.id)
    command = ctx.command.qualified_name if ctx.command else None
    
    # no guild channel set or in allowed globals
    if (not guild or not guild['channel']
            or not command or command in global_commands):
        return True
    elif ctx.channel.id == guild['channel']:
        return True

    if raise_error:
        channel = ctx.bot.get_channel(guild['channel'])
        raise errors.RestrictedChannel(channel)

    return False


def slash_in_guild_channel():
    """Decorator version"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await in_guild_channel(interaction)
    return app_commands.check(predicate)


