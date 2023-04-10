"""
Various functions for making prompts

"""
import discord
import time

from discord.ext import commands
from typing import Optional, Any, Union

from ... import config, mapleio
from .. import errors
from ..resources import EMOJIS


class ConfirmView(discord.ui.View):
    def __init__(self, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.response = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        self.response = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        self.response = False
        self.stop()
        await interaction.response.defer()


class CharacterSelect(discord.ui.Select):
    def __init__(self, user: dict):
        """
        Populated with a user's characters

        Parameters
        ----------
        user: dict
            user data from database

        """
        options = [
            discord.SelectOption(label=char['name'], value=str(i))
            for i, char in enumerate(user['chars'])
        ]
        text = 'Select a character...'
        super().__init__(placeholder=text, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.select = int(self.values[0])
        await interaction.response.defer()


class CharacterSelectView(discord.ui.View):
    def __init__(self, user: dict, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.select = None  # select menu value
        self.response = None  # button value

        select = CharacterSelect(user)
        self.add_item(select)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, row=1)
    async def confirm(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        if self.select is not None:
            self.response = True
            self.stop()
            await interaction.response.defer()
        else:  # reset if nothing selected
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray, row=1)
    async def cancel(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        self.select = None
        self.response = False
        self.stop()
        await interaction.response.defer()


class MessageCache:
    """
    Maintains a cache of messages sent by bot in response to a
    command so that they can be referenced/cleaned subsequently.
    Entries will expire after some time

    Parameters
    ----------
    seconds: int
        the number of seconds to wait before expiring

    """
    def __init__(self, seconds: int):
        super().__init__()
        self.__ttl = seconds
        self.__cache = {}

    def verify_cache_integrity(self) -> None:
        """Loop through cache and remove all expired keys"""
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__cache.items()
                     if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self.__cache[k]

    def get(self, message: discord.Message) -> Any:
        if message.id in self.__cache:
            value, t = self.__cache.get(message.id)
            current_time = time.monotonic()
            if current_time <= (t + self.__ttl):
                return value

    def add(self, message: discord.Message, value: Any) -> None:
        self.__cache[message.id] = (value, time.monotonic())

    def remove(self, message: discord.Message) -> None:
        self.__cache.pop(message.id, None)

    def contains(self, message: discord.Message) -> bool:
        if message.id in self.__cache:
            value, t = self.__cache.get(message.id)
            current_time = time.monotonic()
            return current_time <= (t + self.__ttl)
        else:
            return False

    def __contains__(self, message: discord.Message) -> bool:
        return self.contains(message)

    async def clean_up(
            self,
            message: discord.Message,
            delete: bool = not config.core.debug
    ) -> None:
        """Delete key if exists. Also delete from discord if message"""
        value, t = self.__cache.pop(message.id, (None, None))

        if isinstance(value, discord.Message) and delete:
            try:
                await value.delete()
            except discord.HTTPException:
                pass


async def list_chars(
        ctx: commands.Context,
        user: dict,
        text: str,
        thumbnail: str = None
) -> discord.Message:
    """
    List users chars

    Parameters
    ----------
    ctx: commands.Context
    user: dict
        user data from database
    text: str
        description displayed in embed
    thumbnail: str
        url to the embed thumbnail

    Returns
    -------
    discord.Message
        the message, if sent

    """
    embed = discord.Embed(description=text, color=config.core.embed_color)
    embed.set_author(name='Characters', icon_url=ctx.bot.user.display_avatar.url)

    if not thumbnail:
        thumbnail = ctx.bot.get_emoji_url(EMOJIS['mushparty'])

    embed.set_thumbnail(url=thumbnail)

    # format char names
    char_names = ['-'] * config.core.max_chars

    for i, char in enumerate(user['chars']):
        template = '**{} (default)**' if i == user['default'] else '{}'
        char_names[i] = template.format(char['name'])

    # full width numbers
    char_list = [f'{chr(65297 + i)} \u200b {name}'
                 for i, name in enumerate(char_names)]

    embed.add_field(name='Characters', value='\n'.join(char_list))
    msg = await ctx.send(embed=embed)

    return msg


async def default_char(interaction: discord.Interaction):
    """
    Get the char saved as default (main)

    Parameters
    ----------
    interaction: discord.Interaction

    """
    user = await interaction.client.db.get_user(interaction.user.id)

    if not user or not user['chars']:
        raise errors.NoCharacters

    i = user['default']

    return mapleio.character.Character.from_json(user['chars'][i])


async def get_char(
        interaction: discord.Interaction,
        user: dict,
        name: Optional[str] = None,
        text: Optional[str] = None
) -> Optional[int]:
    """
    Gets char index if name passed. Otherwise, sends embed with
    list of chars. User should react to select

    Parameters
    ----------
    interaction: discord.Interaction
    user: dict
        user data from database
    name: str
        the character to be found
    text:
        description displayed in embed prior to instructions

    Returns
    -------
    Optional[int]
        character index or None if cancelled

    """
    if name:
        chars = user['chars']
        char_iter = (i for i, x in enumerate(chars)
                     if x['name'].lower() == name.lower())
        ind = next(char_iter, None)

        if ind is None:
            raise errors.CharacterNotFound
        else:
            return ind

    # prompt if no name given
    view = CharacterSelectView(user)
    await interaction.edit_original_response(content=text, view=view)
    await view.wait()  # wait for response
    return None if not view.select else int(view.select)


async def confirm_prompt(interaction: discord.Interaction, text) -> bool:
    """
    Prompt user for confirmation

    Parameters
    ----------
    interaction: discord.Interaction
    text: str
        text to display

    Returns
    -------
    bool
        user's selection

    """
    view = ConfirmView()
    await interaction.edit_original_response(content=text, view=view)
    await view.wait()  # wait for selection
    return view.response  # other reactions will timeout
