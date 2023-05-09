"""
Custom errors for bot

"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Iterable

from ... import config


class MushError(app_commands.AppCommandError, commands.CommandError):
    """
    Base error for bot.

    Attributes
    ----------
    cls.default_msg: Optional[str]
      default message to send
    cls.default_see_also: Optional[Iterable[str]]
      default commands to reference
    msg: Optional[str]
      message to send
    see_also: Optional[Iterable[str]]
      commands to reference

    """
    default_msg = f'{config.core.bot_name} failed *cry*'
    default_see_also = None

    def __init__(
            self,
            msg: Optional[str] = None,
            see_also: Optional[Iterable[str]] = None
    ):
        self.msg = msg or self.default_msg
        self.see_also = see_also or self.default_see_also
        super().__init__(self.msg)


class DatabaseWriteError(MushError):
    """Database error when updating"""
    default_msg = 'Problem writing to database. Try again later'


class NoCharacters(MushError):
    """New user. No registered chars"""
    default_msg = 'No registered characters. Please import one to use command'
    default_see_also = ['import']


class CharacterNotFound(MushError):
    """Character not found in database"""
    default_msg = ('Could not find character. List your characters to see '
                   'what characters have been imported')
    default_see_also = ['list chars']


class CharacterAlreadyExists(MushError):
    """Character alraedy exists"""
    default_msg = 'That character already exists. Please use a different name'
    default_see_also = ['list chars']


class MapleIOError(MushError):
    """General MapleIO error"""
    default_msg = 'Maplestory.io request failed or timed out. Try again later'


class BadArgument(MushError):
    """General bad argument error"""
    default_msg = 'Invalid input to argument'


class MissingArgument(MushError):
    """General required arg missing error"""
    default_msg = 'Missing argument'


class UnexpectedFileTypeError(MushError):
    """Wrong file type"""
    default_msg = 'Unexpected file type'


class CharacterParseError(MushError):
    """Error when parsing source data"""
    default_msg = 'There was an error parsing your source data'


class DiscordIOError(MushError):
    """Error reading attachments from Discord"""
    default_msg = 'Error trying to read attached JSON file. Try again later'


class FameError(MushError):
    """Base fame error"""
    default_msg = 'Error while trying to fame'


class SelfFameError(FameError):
    """Error from trying to fame oneself"""
    default_msg = '+1 for self love, but you cannot fame yourself'


class AlreadyFamedError(FameError):
    """Error from already faming member"""
    default_msg = "You've already famed (or defamed) this member today"


class MaxFamesReached(FameError):
    """Error from reaching max # of fames per day"""
    default_msg = "You've reached the fame limit for today"


class RestrictedChannel(MushError):
    """Error from submitting command when channels restricted"""
    def __init__(self, channel: discord.TextChannel):
        self.msg = f'This command can only be used in {channel.mention}'
        super().__init__(self.msg)


class MissingPermissions(MushError):
    """Missing permissions"""
    default_msg = (f'Make sure {config.core.bot_name} has the following '
                   'permissions in this channel.\n\n'
                   '`Manage Webhooks`\n'
                   '`Send Messages`\n'
                   '`Manage Messages\n'
                   '`Send Messages in Threads`\n'
                   '`Create Public/Private Threads`\n'
                   '`Manage Threads`\n'
                   '`Attach Files`\n\n'
                   'Note: permissions may be defaulting to @everyone or '
                   'another role if bot permissions are set to the grey slash')
