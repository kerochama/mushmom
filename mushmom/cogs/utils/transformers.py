"""
Contains transformers for command input validation

"""
from abc import ABC

import discord

from discord.ext import commands
from discord import app_commands
from typing import Optional, TypeVar, Type

from ... import config, mapleio
from ...mapleio.character import Character
from .. import errors
from . import io


class MapleIOURLTransformer(app_commands.Transformer):
    """A valid maplestory.io api call"""
    async def transform(
            self,
            interaction: discord.Interaction,
            value: str
    ) -> str:
        if not value.startswith(config.mapleio.api_url):
            raise errors.BadArgument

        return value


class CharacterTransformer(app_commands.Transformer):
    """Get user character"""
    async def transform(
            self,
            interaction: discord.Interaction,
            value: str
    ) -> Character:
        user = await interaction.client.db.get_user(interaction.user.id)

        if not user or not user['chars']:
            raise errors.NoCharacters

        # passing a name does not prompt anything
        i = await io.get_char_index(interaction, user, name=value)
        return Character.from_json(user['chars'][i])
