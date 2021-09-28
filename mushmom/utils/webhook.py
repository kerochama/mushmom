"""
Functions related to sending messages with webhook

"""
from mushmom import config


async def send_as_author(ctx, *args, **kwargs):
    webhooks = await ctx.channel.webhooks()
    webhook = next((wh for wh in webhooks if wh.name == config.core.hook_name),
                   None)

    # create if does not exist
    if not webhook:
        webhook = await ctx.channel.create_webhook(name=config.core.hook_name)

    await webhook.send(*args, **kwargs, username=ctx.author.display_name,
                       avatar_url=ctx.author.avatar_url)
