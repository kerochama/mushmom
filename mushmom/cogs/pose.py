import discord

from discord.ext import commands
from discord import app_commands

from typing import Optional
from io import BytesIO

from .. import mapleio, config
from .utils import io, errors

from discord.app_commands import Transform
from ..mapleio.character import Character
from .utils.parameters import (
    CharacterTransformer, contains, autocomplete_chars
)


class Pose(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(pose=contains(mapleio.POSES),
                               expression=contains(mapleio.EXPRESSIONS),
                               char=autocomplete_chars)
    async def pose(
            self,
            interaction: discord.Interaction,
            pose: Optional[str] = None,
            expression: Optional[str] = None,
            char: Optional[Transform[Character, CharacterTransformer]] = None,
            frame: int = 0
    ):
        """
        Send a posing character as message

        Parameters
        ----------
        interaction: discord.Interaction
        pose: Optional[Poses]
            A pose from /list poses. If None, use default
        expression: Optional[str]
            An expression from /list expressions. If None, use default
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided
        frame: int
            frame of the animation

        """
        await self.bot.defer(interaction)

        if pose and pose not in mapleio.POSES.values():
            msg = f'**{pose}** is not a valid pose'
            raise errors.BadArgument(msg, see_also=['list poses'])

        if expression and expression not in mapleio.EXPRESSIONS:
            msg = f'**{expression}** is not a valid expression'
            raise errors.BadArgument(msg, see_also=['list expressions'])

        char = char or await io.get_default_char(interaction)
        expression = expression or char.expression
        pose = pose or char.pose

        # create sprite
        min_width = config.core.min_emote_width
        data = await mapleio.api.get_sprite(
            char, pose=pose, expression=expression, min_width=min_width,
            frame=frame, session=self.bot.session
        )

        if data:
            filename = f'{char.name or "char"}_{expression}.png'
            img = discord.File(fp=BytesIO(data), filename=filename)
            if await self.bot.send_as_author(interaction, file=img):
                await self.bot.followup(interaction, content='Pose was sent',
                                        delete_after=0)  # delete immediately
        else:
            raise errors.MapleIOError


async def setup(bot):
    await bot.add_cog(Pose(bot))
