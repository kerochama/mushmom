"""
Functions related to sending messages or reactions

"""
import asyncio

from mushmom import config


async def send_as_author(ctx, *args, **kwargs):
    """
    Use webhook to send a message with authors name and pfp.  Create one
    if does not exist

    :param ctx:
    :param args:
    :param kwargs:
    :return:
    """
    webhooks = await ctx.channel.webhooks()
    webhook = next((wh for wh in webhooks if wh.name == config.core.hook_name),
                   None)

    # create if does not exist
    if not webhook:
        webhook = await ctx.channel.create_webhook(name=config.core.hook_name)

    return await webhook.send(*args, **kwargs,
                              username=ctx.author.display_name,
                              avatar_url=ctx.author.avatar_url)


async def delayed_reaction(ctx, reaction,
                           delay=config.core.delayed_react_time):
    """
    Add a reaction after some time

    :param ctx:
    :param reaction:
    :param delay:
    :return:
    """
    await asyncio.sleep(delay)
    await ctx.message.add_reaction(reaction)
