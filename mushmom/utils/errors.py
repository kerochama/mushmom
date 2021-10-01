"""
Custom errors for bot

"""
import discord

from discord.ext import commands
from mushmom import config


class MushmomError(commands.CommandError):
    pass


class DataNotFound(MushmomError):
    """Not found in database"""
    pass


class DataWriteError(MushmomError):
    """Database error when updating"""
    pass


class MapleIOError(MushmomError):
    """General MapleIO error"""
    pass


class MissingCogError(MushmomError):
    """commands.ExtensionNotLoaded looks like commands.CommandInvokeError

    Using this instead"""
    pass


class UnexpectedFileTypeError(MushmomError):
    pass


class DiscordIOError(MushmomError):
    """Error reading attachments from Discord"""
    pass


class TimeoutError(MushmomError):
    pass


class NoMoreItems(MushmomError):
    """Command error version of discord.NoMoreItems"""
    pass


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

    error = await ctx.send(embed=embed, delete_after=delay if delete_message else None)

    # delete original message after successful send
    if delete_message:
        await ctx.message.delete(delay=delay)

    return error


send = send_error  # alias
