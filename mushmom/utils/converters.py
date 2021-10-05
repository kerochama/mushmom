"""
Contains converters for command input validation

"""
from discord.ext import commands

from .. import config
from ..mapleio import resources


class EmotionConverter(commands.Converter):
    """
    Check if string is in list of emotions from maplestory.io.
    Used with typing.Optional

    """
    async def convert(self, ctx, arg):
        if arg in resources.EMOTIONS:
            return arg

        raise commands.BadArgument(message="Not a valid emotion")


class PoseConverter(commands.Converter):
    """
    Check if string is in list of poses from maplestory.io.
    Used with typing.Optional

    """
    async def convert(self, ctx, arg):
        # poses use O instead of 0
        arg = arg.replace('0', 'O')

        if arg in resources.POSES.values():
            return arg

        raise commands.BadArgument(message="Not a valid pose")


class ImportNameConverter(commands.Converter):
    """
    Used to differentiate name from url.  Maybe can add regex to match valid
    maplestory character names

    """
    async def convert(self, ctx, arg):
        if not arg.startswith(config.mapleio.api_url):
            return arg

        message = "Not a valid character name"
        raise commands.BadArgument(message=message)


class MapleIOURLConverter(commands.Converter):
    """
    Check if valid maplestory.io api call

    """
    async def convert(self, ctx, arg):
        if arg.startswith(config.mapleio.api_url):
            return arg

        message = "Not a valid maplestory.io API call"
        raise commands.BadArgument(message=message)


class CharNameConverter(commands.Converter):
    """
    Check if existing char

    """
    async def convert(self, ctx, arg):
        user = await ctx.bot.db.get_user(ctx.author.id)

        if user and arg.lower() in [x.name.lower() for x in user['chars']]:
            return arg

        raise commands.BadArgument('Character not found')


class FlagConverter(commands.Converter):
    """
    Used for -- options. May replace with a full parser at some point

    """
    async def convert(self, ctx, arg):
        if arg.startswith('--'):
            return arg[2:]  # strip --

        raise commands.BadArgument('Not a valid flag')
