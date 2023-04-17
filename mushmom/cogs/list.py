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
    """
    Command group used for listing values

    """
    list_group = app_commands.Group(name='list',
                                    description='List different things')

    def __init__(self, bot):
        self.bot = bot

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
        static = [emote for emote in mapleio.EXPRESSIONS
                  if emote not in mapleio.ANIMATED] + ['\u200b']
        embed.add_field(name='Static', value='\n'.join(static))
        animated = mapleio.ANIMATED + ['\u200b']
        embed.add_field(name='Animated', value='\n'.join(animated))
        embed.add_field(name='Custom', value='\n'.join([]))

        await self.bot.ephemeral(interaction, embed=embed)

    @list_group.command()
    async def expressions(self, interaction: discord.Interaction):
        """
        List the expressions available for characters

        Parameters
        ----------
        interaction: discord.Interaction

        """
        embed = discord.Embed(
            description=('The following is a list of expressions you can use '
                         'in the generation of your sprite in `/pose`.\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name='Expressions',
                         icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji_url(EMOJIS['mushcheers'])
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text='[GMS v240]')

        # split emotions into 3 lists
        expressions = [mapleio.EXPRESSIONS[i::3] for i in range(3)]  # order not preserved
        expressions = [lst + ['\u200b'] for lst in expressions]
        embed.add_field(name='Expressions', value='\n'.join(expressions[0]))
        embed.add_field(name='\u200b', value='\n'.join(expressions[1]))
        embed.add_field(name='\u200b', value='\n'.join(expressions[2]))

        await self.bot.ephemeral(interaction, embed=embed)

    @list_group.command()
    async def poses(
            self,
            interaction: discord.Interaction,
            show_values: bool = False
    ):
        """
        List the poses available for characters

        Parameters
        ----------
        interaction: discord.Interaction
        show_values: bool
          Display raw values instead of label

        """
        embed = discord.Embed(
            description=('The following is a list of poses you can use in the '
                         'generation of your sprite in `/pose`.\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name='Poses', icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.get_emoji_url(EMOJIS['mushdab']))
        embed.set_footer(text='[GMS v240]')

        label = 'Raw Values' if show_values else 'Poses'
        vals = mapleio.POSES.values() if show_values else mapleio.POSES.keys()
        numbered = [f'`{i+1}`\u3000{x}' for i, x in enumerate(vals)]

        n = len(vals) // 3
        poses = [list(numbered)[i*n:(i+1)*n] for i in range(3)]
        poses = [lst + ['\u200b'] for lst in poses]
        embed.add_field(name=label, value='\n'.join(poses[0]))
        embed.add_field(name='\u200b', value='\n'.join(poses[1]))
        embed.add_field(name='\u200b', value='\n'.join(poses[2]))

        await self.bot.ephemeral(interaction, embed=embed)


class CharacterScrollView(discord.ui.View):
    def __init__(
            self,
            interaction: discord.Interaction,
            user: dict,
            embed: discord.Embed,
            timeout: int = 180
    ):
        super().__init__(timeout=timeout)
        self.orig_interaction = interaction
        self.user = user
        self.curr = user['default']
        self.embed = embed
        self._n = len(user['chars'])

    def get_button(self, label: str):
        return next(x for x in self.children if x.label == label)

    async def _update_char(self, interaction: discord.Interaction, cyc: cycle):
        """Update char based on next in cycle"""
        i = next(cyc)
        while i != self.curr:  # cycle until curr
            i = next(cyc)

        self.curr = next(cyc)
        set_default = self.get_button('Set Default')
        set_default.disabled = self.curr == self.user['default']

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

    @discord.ui.button(label='Set Default', style=discord.ButtonStyle.blurple,
                       disabled=True)
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
            self.stop()  # keep from going to timeout
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
