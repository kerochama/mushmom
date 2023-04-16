"""
Commands to list things

"""
import discord

from discord.ext import commands
from discord import app_commands

from itertools import cycle

from .. import config, mapleio
from .utils import errors

from .resources import EMOJIS
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

        char_names = _fmt_char_names(user, user['default'])
        embed.add_field(name='Characters', value='\n'.join(char_names))

        # image is char
        embed.add_field(name='Preview', value='', inline=False)
        i = user['default']
        char = Character.from_json(user['chars'][i])
        embed.set_image(url=char.url())

        view = CharacterScrollView(interaction, user, i, embed)
        await self.bot.followup(interaction, embed=embed, view=view)

    @list_group.command()
    async def emotes(self, interaction: discord.Interaction):
        """
        List all emotes available

        Parameters
        ----------
        interaction: discord.Interaction

        """
        embed = discord.Embed(
            description=('The following is a list of emotes you can use. '
                         'Call these using the `/mush` command\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name='Emotes', icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji_url(EMOJIS['mushcheers'])
        embed.set_thumbnail(url=thumbnail)

        # static, animated, custom
        static = [emote for emote in mapleio.resources.EXPRESSIONS
                  if emote not in mapleio.resources.ANIMATED] + ['\u200b']
        embed.add_field(name='Static', value='\n'.join(static))
        animated = mapleio.resources.ANIMATED + ['\u200b']
        embed.add_field(name='Animated', value='\n'.join(animated))
        embed.add_field(name='Custom', value='\n'.join([]))

        await self.bot.ephemeral(interaction, embed=embed)


class CharacterScrollView(discord.ui.View):
    def __init__(
            self,
            interaction: discord.Interaction,
            user: dict,
            curr: int,
            embed: discord.Embed,
            timeout: int = 180
    ):
        super().__init__(timeout=timeout)
        self.orig_interaction = interaction
        self.user = user
        self.curr = curr
        self.embed = embed
        self._n = len(user['chars'])

        # disabled if already default
        self.set_default_button.disabled = True

    @property
    def set_default_button(self):
        return next(x for x in self.children if x.label == 'Set Default')

    async def _update_char(self, interaction: discord.Interaction, cyc: cycle):
        """Update char based on next in cycle"""
        i = next(cyc)
        while i != self.curr:  # cycle until curr
            i = next(cyc)

        self.curr = next(cyc)
        self.set_default_button.disabled = self.curr == self.user['default']

        # update list
        chars = _fmt_char_names(self.user, self.curr)
        self.embed.set_field_at(0, name='Characters', value='\n'.join(chars))

        # update image
        char = Character.from_json(self.user['chars'][self.curr])
        self.embed.set_image(url=char.url())

        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label='\u2190')
    async def prev(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        cyc = cycle(reversed(range(self._n)))
        await self._update_char(interaction, cyc)

    @discord.ui.button(label='\u2192')
    async def next(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        cyc = cycle(range(self._n))
        await self._update_char(interaction, cyc)

    @discord.ui.button(label='Set Default', style=discord.ButtonStyle.blurple)
    async def set_default(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        update = {'default': self.curr}
        ret = await interaction.client.db.set_user(interaction.user.id, update)

        if ret and ret.acknowledged:
            name = self.user['chars'][self.curr]['name']
            text = f'Default was changed to **{name}**'
            await interaction.response.edit_message(content=text,
                                                    embed=None, view=None)
        else:
            raise errors.DatabaseWriteError

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True

        await self.orig_interaction.edit_original_response(view=self)


def _fmt_char_names(user: dict, bold_i: int):
    """Format char names for chars embed"""
    char_names = ['-'] * config.core.max_chars  # placeholder

    # add bullets and bold current selection
    for i, char in enumerate(user['chars']):
        default = '{} (default)' if i == user['default'] else '{}'
        bold = '\u2726 \u200b **{}**' if i == bold_i else '\u2727 \u200b {}'
        char_names[i] = bold.format(default).format(char['name'])

    # extra space
    char_names += ['\u200b']
    return char_names


async def setup(bot):
    await bot.add_cog(List(bot))
