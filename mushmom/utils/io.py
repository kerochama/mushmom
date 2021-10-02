"""
Functions related to sending messages or reactions

"""
import discord
import asyncio
import time

from .. import config


class ReplyCache:
    def __init__(self, seconds):
        """
        Maintains a cache of messages sent by bot in response to a command
        so that they can be referenced/cleaned subsequently

        :param seconds:
        """
        self.__ttl = seconds
        self.__cache = {}
        super().__init__()

    def verify_cache_integrity(self):
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__cache.items()
                     if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self.__cache[k]

    def get(self, ctx):
        return self.__cache.get(ctx.message.id, None)

    def add(self, ctx, reply):
        self.__cache[ctx.message.id] = (reply, time.monotonic())

    def remove(self, ctx):
        self.__cache.pop(ctx.message.id, None)

    def contains(self, ctx):
        return ctx.message.id in self.__cache

    def __contains__(self, ctx):
        return self.contains(ctx)

    async def clean_up(self, ctx, delete=not config.core.debug):
        reply = self.__cache.pop(ctx, None)

        if reply and delete:
            try:
                await reply.delete()
            except discord.HTTPException:
                pass


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
