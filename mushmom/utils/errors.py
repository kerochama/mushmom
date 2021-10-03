"""
Custom errors for bot

"""
import discord

from discord.ext import commands


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


class CharacterParseError(MushmomError):
    """Error when parsing source data"""
    pass


class DiscordIOError(MushmomError):
    """Error reading attachments from Discord"""
    pass


class TimeoutError(MushmomError):
    pass


class NoMoreItems(MushmomError):
    """Command error version of discord.NoMoreItems"""
    pass
