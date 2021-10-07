"""
Contains converters for command input validation

"""
from discord.ext import commands

from .. import config
from ..mapleio import resources


class EmotionConverter(commands.Converter):
    """String in list of emotions from maplestory.io"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg in resources.EMOTIONS:
            return arg

        raise commands.BadArgument(message="Not a valid emotion")


class PoseConverter(commands.Converter):
    """String is in list of poses from maplestory.io"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        # poses use O instead of 0
        arg = arg.replace('0', 'O')

        if arg in resources.POSES.values():
            return arg

        raise commands.BadArgument(message="Not a valid pose")


class ImportNameConverter(commands.Converter):
    """Used to differentiate name from API call"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if not arg.startswith(config.mapleio.api_url):
            return arg

        message = "Not a valid character name"
        raise commands.BadArgument(message=message)


class MapleIOURLConverter(commands.Converter):
    """A valid maplestory.io api call"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.startswith(config.mapleio.api_url):
            return arg

        message = "Not a valid maplestory.io API call"
        raise commands.BadArgument(message=message)


class CharNameConverter(commands.Converter):
    """Existing character"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        user = await ctx.bot.db.get_user(ctx.author.id)

        if user and arg.lower() in [x.name.lower() for x in user['chars']]:
            return arg

        raise commands.BadArgument('Character not found')


class OptionConverter(commands.Converter):
    """Used for -- options"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.startswith('--'):
            return arg[2:]  # strip --

        raise commands.BadArgument('Not a valid option')


class CommandConverter(commands.Converter):
    """Check if command exists"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if ctx.bot.get_command(arg):
            return arg

        raise commands.BadArgument('Command not found')
