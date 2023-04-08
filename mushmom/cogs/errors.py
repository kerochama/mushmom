"""
Error handler

"""
import sys
import discord
import traceback

from discord.ext import commands
from discord import app_commands
from typing import Optional, Iterable

from .. import config
from . import reference
from .resources import EMOJIS


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        bot.tree.error(coro=self.__dispatch_to_app_command_handler)

    async def __dispatch_to_app_command_handler(
            self,
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
    ) -> None:
        self.bot.dispatch("app_command_error", interaction, error)

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(
            self,
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError
    ) -> None:
        """
        Override default error handler to always run. Errors messages
        are pulled from cogs.reference.ERRORS.

        Local error handlers can still be used

        Parameters
        ----------
        interaction: discord.Interaction
        error: Exception

        """
        cmd = interaction.command.name
        err = error.__class__.__name__

        if (cmd in reference.ERRORS.keys()   # command specific error
                and err in reference.ERRORS[cmd].keys()):
            specs = reference.ERRORS[cmd][err]
        elif err in reference.ERRORS['_default'].keys():  # general error
            specs = reference.ERRORS['_default'][err]
        else:
            if not isinstance(error, app_commands.CheckFailure):
                print(f'Ignoring exception in command `{cmd}`:', file=sys.stderr)
                traceback.print_exception(type(error), error, error.__traceback__,
                                          file=sys.stderr)
            return

        await self.send_error(interaction, *specs.values())

    async def send_error(
        self,
        interaction: discord.Interaction,
        text: Optional[str] = None,
        see_also: Optional[Iterable[str]] = None,
        raw_content: Optional[str] = None
    ) -> discord.WebhookMessage:
        """
        Send a message to ctx.channel with an error message. The
        original message and the error message will auto-delete after
        a few seconds to keep channel clean

        Parameters
        ----------
        interaction: discord.Interaction
        text: Optional[str]
            the message to send in embed
        see_also: Optional[Iterable[str]]
            list of fully qualified command names to reference
        raw_content: Optional[str]
            content to pass directly to send, outside embed

        Returns
        -------
        discord.WebhookMessage
            the error message that was sent

        """
        # defaults
        text = text or f'{config.core.bot_name} failed *cry*'
        text += '\n\u200b'

        # send error
        embed = discord.Embed(description=text, color=config.core.embed_color)
        embed.set_author(name='Error',
                         icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.get_emoji_url(EMOJIS['mushshock']))

        if see_also:
            fmt = [f'`{cmd}`' for cmd in see_also]
            embed.add_field(name='See also', value=', '.join(fmt))

        coro = (self.bot.followup if interaction.response.is_done()
                else self.bot.ephemeral)
        return await coro(interaction, content=raw_content, embed=embed,
                          delete_after=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Errors(bot))


# Custom errors
class MushError(app_commands.AppCommandError):
    """Base bot error"""
    pass


class NoCharacters(MushError):
    """New user. No registered chars"""
    pass


class CharacterNotFound(MushError):
    """Character not found in database"""
    pass


class MapleIOError(MushError):
    """General MapleIO error"""
    pass
