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
from .utils import errors
from .resources import EMOJIS


class ErrorHandler(commands.Cog):
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
            error: app_commands.AppCommandError
    ) -> None:
        """
        Override default error handler to send ephemeral messages

        Parameters
        ----------
        interaction: discord.Interaction
        error: Exception

        """
        cmd = interaction.command.name

        if isinstance(error, errors.MushError):
            info = {'msg': error.msg, 'see_also': error.see_also}
            await self.send_error(interaction, **info)
        else:
            if not isinstance(error, app_commands.CheckFailure):
                print(f'Ignoring exception in command `{cmd}`:', file=sys.stderr)
                traceback.print_exception(type(error), error, error.__traceback__,
                                          file=sys.stderr)

    async def send_error(
        self,
        interaction: discord.Interaction,
        msg: Optional[str] = None,
        see_also: Optional[Iterable[str]] = None,
        raw_content: Optional[str] = None
    ) -> discord.WebhookMessage:
        """
        Send an ephemeral message with an error

        Parameters
        ----------
        interaction: discord.Interaction
        msg: Optional[str]
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
        msg = msg or f'{config.core.bot_name} failed *cry*'
        msg += '\n\u200b'

        # send error
        embed = discord.Embed(description=msg, color=config.core.embed_color)
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
    await bot.add_cog(ErrorHandler(bot))
