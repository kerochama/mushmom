"""
Contains command checks

"""
from discord.ext import commands


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
    message = ctx.message

    checks = (
        message.author == ctx.bot.user,  # ignore self
        message.author.bot,  # ignore other bots
    )

    return not any(checks)
