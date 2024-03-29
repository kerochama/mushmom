"""
Contains transformers for command input validation

"""
from abc import ABC

import discord

from discord.ext import commands
from discord import app_commands
from typing import Union

from ... import config, mapleio
from ...mapleio.character import Character
from . import errors
from . import io


class MapleIOURLTransformer(app_commands.Transformer):
    """A valid maplestory.io api call"""
    async def transform(
            self,
            interaction: discord.Interaction,
            value: str
    ) -> str:
        if not value.startswith(config.mapleio.api_url):
            msg = 'Not a valid maplestory.io API call'
            raise errors.BadArgument(msg)

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


async def autocomplete_chars(interaction, current):
    """
    Autocomplete for user's characters. Note: db call is cached,
    so not clobbering the database

    Parameters
    ----------
    interaction: discord.Interaction
    current: str

    Returns
    -------
        List[app_commands.Choice]
    """
    user = await interaction.client.db.get_user(interaction.user.id)
    if user:
        return [app_commands.Choice(name=char['name'], value=char['name'])
                for char in user['chars']
                if current.lower() in char['name'].lower()]
    return []


def contains(choices: Union[list, dict]):
    """
    Autocomplete function for filtering choices

    Parameters
    ----------
    choices: Union[list, dict]
      A list of choices or label: value choice options

    Returns
    -------
      coroutine to be used as autocomplete callback

    """
    if isinstance(choices, list):
        choices = dict(zip(choices, choices))

    async def wrapper(interaction, current):
        return [app_commands.Choice(name=k, value=v)
                for k, v in choices.items()
                if current.lower() in k.lower()][:25]

    return wrapper
