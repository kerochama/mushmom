"""
Custom errors for bot

"""
import discord

from discord.ext import commands

from mushmom import config


async def send_error(ctx, text, delete_message=True, delay=5):
    """
    Generic function to send formatted error

    :param ctx:
    :param text:
    :param delete_message:
    :param delay: 5 seconds
    :return:
    """
    emoji = next((e for e in ctx.bot.emojis if e.name == 'mushshocked'), None)

    # send error
    embed = discord.Embed(description=text, color=config.EMBED_COLOR)
    embed.set_author(name='Error')

    if emoji:
        url = f'https://cdn.discordapp.com/emojis/{emoji.id}.png'
        embed.set_thumbnail(url=url)

    await ctx.send(embed=embed, delete_after=delay if delete_message else None)

    # delete original message
    if delete_message:
        await ctx.message.delete(delay=delay)


class DataNotFoundError(commands.CommandError):
    pass


class MapleIOError(commands.CommandError):
    pass
