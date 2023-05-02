"""
Contains command checks

"""
import discord

from discord.ext import commands
from discord import app_commands

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


async def in_guild_channel(ctx: commands.Context) -> bool:
    """
    Checks if message was sent in designated channel.  If no channel
    is set for the guild, all channels will pass

    Commands or cogs in global_commands/cogs will bypass this check

    Parameters
    ----------
    ctx: commands.Context

    Returns
    -------
    bool
        whether or not message is in an acceptable channel

    """
    guild = await ctx.bot.db.get_guild(ctx.guild.id)
    command = ctx.command.qualified_name if ctx.command else None
    
    # no guild channel set or in allowed globals
    if (not guild or not guild['channel']
            or not command or command in global_commands):
        return True
    elif ctx.channel.id == guild['channel']:
        return True

    channel = ctx.bot.get_channel(guild['channel'])
    raise errors.RestrictedChannel(channel)


async def _slash_in_guild_channel(interaction: discord.Interaction) -> bool:
    """Slash command version of in_guild_channel"""
    ctx = await interaction.client.get_context(interaction)
    return await in_guild_channel(ctx)


def slash_in_guild_channel():
    """Decorator verson"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await _slash_in_guild_channel(interaction)
    return app_commands.check(predicate)
