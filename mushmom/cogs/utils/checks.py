"""
Contains command checks

"""
from discord.ext import commands


global_commands = (  # commands that will bypass channel check
    'emote',
    'sprite',
    'set',
    'reset'
)

global_cogs = (
    'Actions'
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
    return not ctx.author.bot


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
    cog = ctx.command.cog_name if ctx.command else None
    
    # no guild channel set or in allowed globals
    if (not guild or not guild['channel']
            or command in global_commands or cog in global_cogs):
        return True
    else:
        return ctx.channel.id == guild['channel']
