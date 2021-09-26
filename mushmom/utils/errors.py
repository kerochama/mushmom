"""
Custom errors for bot

"""
import discord

from discord.ext import commands

from mushmom import config


# Errors not auto-deleted when DEBUG on
async def send_error(ctx, text, delete_message=not config.DEBUG,
                     delay=config.DEFAULT_DELAY, append='', fields=None):
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
    # send error
    embed = discord.Embed(description=text + append,
                          color=config.EMBED_COLOR)
    embed.set_author(name='Error', icon_url=ctx.bot.user.avatar_url)
    embed.set_thumbnail(url=config.EMOJIS['mushshock'])

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
    def __init__(self):
        # keep track of message replies to clean up when error
        # does not have to be a direct reply, just response to command
        self._reply_cache = {
            # message.id: [replies]
        }

    def register(self, ctx, reply):
        msg_id = ctx.message.id

        if msg_id in self._reply_cache:
            self._reply_cache[msg_id].append(reply)
        else:
            self._reply_cache[msg_id] = [reply]

    def unregister(self, ctx):
        return self._reply_cache.pop(ctx.message.id, None)

    def clean(self, ctx, delete=not config.DEBUG):
        """
        Try to delete and remove from cache

        :param ctx:
        :param delete:
        :return:
        """
        replies = self.unregister(ctx) or []

        if not delete:
            return

        for reply in replies:
            try:
                reply.delete()
            except (discord.Forbidden,discord.NotFound, discord.HTTPException):
                pass


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


