"""
Contains converters for command input validation

"""
from discord.ext import commands
from typing import Optional, TypeVar, Type

from ... import config, mapleio
from ...mapleio.character import Character
from . import errors, prompts


class SimpleNotConverter(commands.Converter):
    """
    Inverts simple converters that just return the arg if a condition
    is passed. (i.e. everything used in this bot)

    """
    __ref_cvtr__: Type[type]

    async def convert(self, ctx: commands.Context, arg: str) -> str:
        try:  # works then raise error
            await self.__class__.__ref_cvtr__.convert(self, ctx, arg)
        except commands.BadArgument:
            return arg

        raise commands.BadArgument('Passed reference converter')


class EmotionConverter(commands.Converter):
    """String in list of emotions from maplestory.io"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg in mapleio.resources.EMOTIONS:
            return arg

        raise commands.BadArgument(message="Not a valid emotion")


class PoseConverter(commands.Converter):
    """String is in list of poses from maplestory.io"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        # poses use O instead of 0
        arg = arg.replace('0', 'O')

        if arg in mapleio.resources.POSES.values():
            return arg

        raise commands.BadArgument(message="Not a valid pose")


class MapleIOURLConverter(commands.Converter):
    """A valid maplestory.io api call"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.startswith(config.mapleio.api_url):
            return arg

        message = "Not a valid maplestory.io API call"
        raise commands.BadArgument(message=message)


class NotMapleIOURLConverter(SimpleNotConverter):
    """Anything but maplestory.io api call"""
    __ref_cvtr__ = MapleIOURLConverter


class CommandConverter(commands.Converter):
    """Check if command exists"""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if ctx.bot.get_command(arg):
            return arg

        raise commands.BadArgument('Command not found')


class CharacterConverter(commands.Converter):
    """Get user character"""
    async def convert(self, ctx: commands.Context, arg: str) -> Character:
        user = await ctx.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        # passing a name does not prompt anything
        i = await prompts.get_char(ctx, user, name=arg)
        return Character.from_json(user['chars'][i])


# Flag Converters
SF = TypeVar('SF', bound='FlagConverter')


class StrictFlagConverter(commands.FlagConverter):
    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> SF:
        """
        Flags must start at beginning of argument

        Parameters
        ----------
        ctx: commands.Context
        argument: str
            the argument to convert

        Returns
        -------
        StrictFlagConverter
            The flag converter instance with all flags parsed

        """
        self = await super().convert(ctx, argument)

        # if first flag not at beginning then something was sent before flags
        flag_iter = (x for x in cls.__commands_flag_regex__.finditer(argument))
        match = next(flag_iter, None)
        if (match and match.start() > 0) or (argument and not match):
            raise errors.UnparsedArgsError

        return self


async def default_char(ctx: commands.Context):
    """
    Get the char saved as default (main)

    Parameters
    ----------
    ctx: commands.Context

    """
    user = await ctx.bot.db.get_user(ctx.author.id)

    if not user or not user['chars']:
        raise errors.NoMoreItems

    i = user['default']

    return Character.from_json(user['chars'][i])


class ImgFlags(StrictFlagConverter, delimiter=' '):
    """Get a character"""
    char: Optional[CharacterConverter] = commands.flag(
        name='--char',
        aliases=['-c'],
        default=default_char
    )


class InfoFlags(StrictFlagConverter, delimiter=' '):
    """Settings for profile info"""
    name: Optional[str] = commands.flag(
        name='--name', aliases=['-n'], default=None)
    action: Optional[PoseConverter] = commands.flag(
        name='--pose', aliases=['-p'], default=None)
    emotion: Optional[EmotionConverter] = commands.flag(
        name='--emotion', aliases=['-e'], default=None)
    job: Optional[str] = commands.flag(
        name='--job', aliases=['-j'], default=None)
    game: Optional[str] = commands.flag(
        name='--game', aliases=['-G'], default=None)
    server: Optional[str] = commands.flag(
        name='--server', aliases=['-s'], default=None)
    guild: Optional[str] = commands.flag(
        name='--guild', aliases=['-g'], default=None)
