"""
Contains command checks

"""
from discord.ext import commands


global_commands = (  # commands that will bypass channel check
    'emote',
    'sprite',
    'set',
    'reset',
    'channel'  # can be run anywhere to find channel
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

    Commands in global_commands will bypass this check

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

    # has guild setting and command sent thats not in global_commands
    if (guild and guild['channel'] and command
            and command not in global_commands):
        return ctx.channel.id == guild['channel']
    else:
        return True
