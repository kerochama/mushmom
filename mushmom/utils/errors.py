"""
Custom errors for bot

"""
import discord

from discord.ext import commands
from datetime import datetime

from mushmom import config


# Errors not auto-deleted when DEBUG on
async def send_error(ctx, text=None, delete_message=not config.core.debug,
                     delay=config.core.default_delay, append='', fields=None):
    """
    Generic function to send formatted error

    :param ctx:
    :param text:
    :param delete_message:
    :param delay: 5 seconds
    :param append: extra text to append
    :param fields:
    :return:
    """
    if text is None:
        text = 'Mushmom failed *cry*'

    # send error
    embed = discord.Embed(description=text + append,
                          color=config.core.embed_color)
    embed.set_author(name='Error', icon_url=ctx.bot.user.avatar_url)
    embed.set_thumbnail(url=ctx.bot.get_emoji_url(config.emojis.mushshock))

    # add fields
    if fields:
        for name, value in fields.items():
            embed.add_field(name=name, value=value)

    await ctx.send(embed=embed, delete_after=delay if delete_message else None)

    # delete original message
    if delete_message:
        await ctx.message.delete(delay=delay)


send = send_error  # alias


class ReplyCache:
    def __init__(self, timeout=300):
        """
        Maintains a cache of messages sent by bot in response to a command
        so that they can be referenced/cleaned subsequently

        :param timeout: seconds passed signifying can be deleted
        """
        # keep track of message replies to clean up when error
        # does not have to be a direct reply, just response to command
        self._reply_cache = {
            # message.id: [(reply, ts)]
        }
        self.timeout = timeout  # seconds

    def register(self, ctx, reply):
        msg_id = ctx.message.id
        record = (reply, datetime.utcnow())

        if msg_id in self._reply_cache:
            self._reply_cache[msg_id].append(record)
        else:
            self._reply_cache[msg_id] = [record]

    def unregister(self, ctx):
        return self._reply_cache.pop(ctx.message.id, None)

    def clean(self, ctx, delete=not config.core.debug):
        """
        Try to delete and remove from cache

        :param ctx:
        :param delete:
        :return:
        """
        replies = self.unregister(ctx) or []

        if not delete:
            return

        for reply, ts in replies:
            try:
                reply.delete()
            except (discord.Forbidden,discord.NotFound, discord.HTTPException):
                pass

    def run_garbage_collector(self):
        """
        Loop through cache and remove anything older than timeout

        :return:
        """
        # clean each list
        for msg_id, replies in self._reply_cache.items():
            cleansed = [(reply, ts) for reply, ts in replies
                        if (datetime.utcnow() - ts).seconds <= self.timeout]
            self._reply_cache[msg_id] = cleansed

        # clean dict
        for msg_id in list(self._reply_cache.keys()):
            if not self._reply_cache[msg_id]:  # empty list
                del self._reply_cache[msg_id]


class DataNotFound(commands.CommandError):
    pass


class DataWriteError(commands.CommandError):
    pass


class MapleIOError(commands.CommandError):
    pass


class UnexpectedFileTypeError(commands.CommandError):
    pass


class DiscordIOError(commands.CommandError):
    pass


class TimeoutError(commands.CommandError):
    pass


class NoMoreItems(commands.CommandError):
    """
    Command error version of discord.NoMoreItems

    """
    pass
