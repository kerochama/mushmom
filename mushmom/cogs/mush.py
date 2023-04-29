"""
Main commands for sending emotes

"""
import discord

from discord.ext import commands
from discord import app_commands

from typing import Optional
from io import BytesIO
from aenum import Enum

from .. import mapleio
from .utils import io, errors

from discord.app_commands import Transform
from ..mapleio.character import Character
from .utils.parameters import (
    CharacterTransformer, contains, autocomplete_chars
)


class Mush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(emote=contains(mapleio.EXPRESSIONS),
                               char=autocomplete_chars)
    async def mush(
            self,
            interaction: discord.Interaction,
            emote: str,
            char: Optional[Transform[Character, CharacterTransformer]] = None
    ) -> None:
        """
        Send maple emotes of your character

        Parameters
        ----------
        interaction: discord.Interaction,
        emote: str
            the emote to send
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided

        """
        await self.bot.defer(interaction)

        if emote not in mapleio.EXPRESSIONS:
            msg = f'**{emote}** is not a valid emote'
            raise errors.BadArgument(msg, see_also=['list emotes'])

        char = char or await io.get_default_char(interaction)

        # create emote
        coro, ext = (
            (mapleio.api.get_animated_emote, 'gif')
            if emote in mapleio.ANIMATED
            else (mapleio.api.get_emote, 'png')
        )
        data = await coro(char, expression=emote, min_width=300,
                          session=self.bot.session)

        if data:
            filename = f'{char.name or "char"}_{emote}.{ext}'
            img = discord.File(fp=BytesIO(data), filename=filename)
            if await self.bot.send_as_author(interaction, file=img):
                await self.bot.followup(interaction, content='Emote was sent',
                                        delete_after=0)  # delete immediately
        else:
            raise errors.MapleIOError


async def setup(bot):
    await bot.add_cog(Mush(bot))
