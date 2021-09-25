"""
Contains converters for command input validation

"""
from discord.ext import commands

from mushmom import config
from mushmom.mapleio import states


class EmotionConverter(commands.Converter):
    """
    Check if string is in list of emotions from maplestory.io.
    Used with typing.Optional

    """
    async def convert(self, ctx, arg):
        if arg in states.EMOTIONS:
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

        if arg in states.POSES.values():
            return arg

        raise commands.BadArgument(message="Not a valid pose")


class ImportNameConverter(commands.Converter):
    """
    Used to differentiate name from url.  Maybe can add regex to match valid
    maplestory character names

    """
    async def convert(self, ctx, arg):
        if not arg.startswith(config.MAPLEIO_API):
            return arg

        message = "Not a valid character name"
        raise commands.BadArgument(message=message)


class MapleIOURLConverter(commands.Converter):
    """
    Check if valid maplestory.io api call

    """
    async def convert(self, ctx, arg):
        if arg.startswith(config.MAPLEIO_API):
            return arg

        message = "Not a valid maplestory.io API call"
        raise commands.BadArgument(message=message)
