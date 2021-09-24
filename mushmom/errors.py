"""
Custom errors for bot

"""
import discord

from discord.ext import commands

from mushmom import config


# Errors not auto-deleted when DEBUG on
async def send_error(ctx, text, delete_message=not config.DEBUG, delay=10,
                     append=''):
    """
    Generic function to send formatted error

    :param ctx:
    :param text:
    :param delete_message:
    :param delay: 5 seconds
    :param append: extra text to append
    :return:
    """
    emoji = next((e for e in ctx.bot.emojis if e.name == 'mushshocked'), None)

    # send error
    embed = discord.Embed(description=text + append_text,
                          color=config.EMBED_COLOR)
    embed.set_author(name='Error')

    if emoji:
        url = f'https://cdn.discordapp.com/emojis/{emoji.id}.png'
        embed.set_thumbnail(url=url)

    await ctx.send(embed=embed, delete_after=delay if delete_message else None)

    # delete original message
    if delete_message:
        await ctx.message.delete(delay=delay)


send = send_error  # alias


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
