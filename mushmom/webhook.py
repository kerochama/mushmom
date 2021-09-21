HOOK_NAME = 'Mushmom'


async def send_as_author(ctx, *args, **kwargs):
    webhooks = await ctx.channel.webhooks()
    webhook = next((wh for wh in webhooks if wh.name == HOOK_NAME), None)

    # create if does not exist
    if not webhook:
        webhook = await ctx.channel.create_webhook(name=HOOK_NAME)

    await webhook.send(*args, **kwargs, username=ctx.author.display_name,
                       avatar_url=ctx.author.avatar_url)
