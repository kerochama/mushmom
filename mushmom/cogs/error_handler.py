"""
Error handler

"""
import sys
import discord
import traceback
from datetime import datetime

from discord.ext import commands
from discord import app_commands
from typing import Optional, Iterable

from .. import config
from .utils import errors
from ..resources import EMOJIS


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
        error: app_commands.AppCommandError

        """
        cmd = interaction.command.name

        if isinstance(error, errors.MushError):
            info = {'msg': error.msg, 'see_also': error.see_also}
            embed = self.format_error(**info)
        elif isinstance(error.__cause__, discord.Forbidden):
            # CommandInvokeError from e
            embed = self.format_error(errors.MissingPermissions.default_msg)
        else:
            # generic message
            embed = self.format_error(errors.MushError.default_msg)
            print(f'Ignoring exception in command `{cmd}`:', file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)

        # determine coro for sending
        error_args = {
            'embed': embed,
            'ephemeral': True
        }

        if interaction.response.is_done():
            try:  # try to get orig message
                orig_msg = await interaction.original_response()
            except discord.NotFound:
                orig_msg = None

            if orig_msg and not orig_msg.flags.ephemeral:
                await orig_msg.delete()  # delete if not ephemeral
                coro = interaction.followup.send
            else:
                coro = interaction.edit_original_response
                error_args.pop('ephemeral')
        else:
            coro = interaction.response.send_message

        await coro(**error_args)

    @commands.Cog.listener()
    async def on_command_error(
            self,
            ctx: commands.Context,
            error: commands.CommandError
    ) -> None:
        """
        Override default command error

        Parameters
        ----------
        ctx: commands.Context
        error: commands.CommandError

        """
        if not ctx.command:  # not command
            return

        cmd = ctx.command.qualified_name

        if isinstance(error, commands.MissingPermissions):
            embed = self.format_error(str(error))
        elif isinstance(error, errors.MushError):
            info = {'msg': error.msg, 'see_also': error.see_also}
            embed = self.format_error(**info)
        else:
            embed = self.format_error(errors.MushError.default_msg)
            print(f'Ignoring exception in command `{cmd}`:', file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)

        try:  # try to cleanup the original message
            await ctx.message.delete(delay=10)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        await ctx.send(embed=embed, delete_after=10)

    def format_error(
            self,
            msg: Optional[str] = None,
            see_also: Optional[Iterable[str]] = None,
    ) -> discord.Embed:
        """
        Format error into an embed

        Parameters
        ----------
        msg: Optional[str]
            the message to send in embed
        see_also: Optional[Iterable[str]]
            list of fully qualified command names to reference

        Returns
        -------
        discord.Embed
            the embed error

        """
        # defaults
        msg = msg or f'{config.core.bot_name} failed *cry*'
        msg += '\n\u200b'

        # send error
        embed = discord.Embed(description=msg, color=config.core.embed_color)
        embed.set_author(name='Error',
                         icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.get_emoji(EMOJIS['mushshock'].id).url)

        if see_also:
            fmt = [f'`/{cmd}`' for cmd in see_also]
            embed.add_field(name='See also', value=', '.join(fmt))

        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
