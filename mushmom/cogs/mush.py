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

Emotes = Enum('Emotes', mapleio.EXPRESSIONS)


class Mush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(char=autocomplete_chars)
    async def mush(
            self,
            interaction: discord.Interaction,
            emote: Emotes,
            char: Optional[Transform[Character, CharacterTransformer]] = None
    ) -> None:
        """
        Send maple emotes of your character

        Parameters
        ----------
        interaction: discord.Interaction,
        emote: Emotes
            the emote to send
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided

        """
        await self.bot.defer(interaction)
        char = char or await io.get_default_char(interaction)

        # create emote
        coro, ext = (
            (mapleio.api.get_animated_emote, 'gif')
            if emote.name in mapleio.ANIMATED
            else (mapleio.api.get_emote, 'png')
        )
        data = await coro(char, expression=emote.name, min_width=300,
                          session=self.bot.session)

        if data:
            filename = f'{char.name or "char"}_{emote.name}.{ext}'
            img = discord.File(fp=BytesIO(data), filename=filename)
            if await self.bot.send_as_author(interaction, file=img):
                await self.bot.followup(interaction, content='Emote was sent',
                                        delete_after=0)  # delete immediately
        else:
            raise errors.MapleIOError


async def setup(bot):
    await bot.add_cog(Mush(bot))
