"""
Commands to list things

"""
import discord

from discord.ext import commands
from discord import app_commands

from typing import Optional
from io import BytesIO
from aenum import Enum

from .. import config
from . import errors
from .utils import io

from ..mapleio.character import Character


class List(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    list_group = app_commands.Group(name='list', description='List different things')

    @list_group.command()
    async def chars(self, interaction: discord.Interaction):
        """
        List all characters registered

        Parameters
        ----------
        interaction: discord.Interaction

        """
        await self.bot.defer(interaction)
        user = await self.bot.db.get_user(interaction.user.id)

        if not user:
            raise errors.NoCharacters

        text = 'Your mushable characters\n\u200b'
        embed = discord.Embed(description=text, color=config.core.embed_color)
        embed.set_author(name='Characters',
                         icon_url=interaction.client.user.display_avatar.url)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # format char names
        char_names = ['-'] * config.core.max_chars

        for i, char in enumerate(user['chars']):
            template = '**{} (default)**' if i == user['default'] else '{}'
            char_names[i] = template.format(char['name'])

        # full width numbers
        char_list = [f'\u2727 \u200b {name}'  # shine outline
                     for i, name in enumerate(char_names)]
        char_list += ['\u200b']  # extra space

        embed.add_field(name='Characters', value='\n'.join(char_list))

        # image is char
        embed.add_field(name='Preview', value='', inline=False)
        i = user['default']
        char = Character.from_json(user['chars'][i])
        embed.set_image(url=char.url())

        await self.bot.followup(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(List(bot))
