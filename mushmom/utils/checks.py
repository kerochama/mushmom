"""
Contains command checks

"""


async def not_bot(ctx):
    """
    Check if send is a bot

    :param ctx:
    :return:
    """
    message = ctx.message

    checks = (
        message.author == ctx.bot.user,  # ignore self
        message.author.bot,  # ignore other bots
    )

    return not any(checks)
