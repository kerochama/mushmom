"""
Character commands

"""
import discord

from discord import app_commands
from discord.ext import commands

from .utils import errors, io
from .utils.parameters import autocomplete_chars


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.autocomplete(char=autocomplete_chars)
    async def delete(
            self,
            interaction: discord.Interaction,
            char: str
    ) -> None:
        """
        Delete the specified character

        Parameters
        ----------
        interaction: discord.Interaction
        char: str
            the character to delete

        """
        await self.bot.defer(interaction)
        user = await self.bot.db.get_user(interaction.user.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        default_i = user['default']
        del_i = await io.get_char_index(interaction, user, name=char)

        # remove char and handle default
        if del_i < default_i:
            default_i -= 1  # decrement
        elif del_i == default_i:
            default_i = 0  # if deleted default, set to first

        char = user['chars'].pop(del_i)
        update = {'default': default_i, 'chars': user['chars']}
        ret = await self.bot.db.set_user(interaction.user.id, update)

        if ret.acknowledged:
            text = f'**{char["name"]}** was deleted'
            await self.bot.followup(interaction, content=text)
        else:
            raise errors.DataWriteError

    @app_commands.command()
    @app_commands.autocomplete(char=autocomplete_chars)
    async def rename(
            self,
            interaction: discord.Interaction,
            char: str,
            name: str
    ):
        """
        Rename a character with the new name given

        Parameters
        ----------
        interaction: discord.Interaction
        char: str
            the character to rename
        name: str
            new character name

        """
        await self.bot.defer(interaction)
        user = await self.bot.db.get_user(interaction.user.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        # check if new_name exists
        if name in [c['name'] for c in user['chars']]:
            raise errors.CharacterAlreadyExists

        # get char to replace
        i = await io.get_char_index(interaction, user, name=char)

        user['chars'][i]['name'] = name
        update = {'chars': user['chars']}
        ret = await self.bot.db.set_user(interaction.user.id, update)

        if ret.acknowledged:
            text = f'**{char}** was renamed **{name}**'
            await self.bot.followup(interaction, content=text)
        else:
            raise errors.DataWriteError


async def setup(bot):
    await bot.add_cog(Characters(bot))
