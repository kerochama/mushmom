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

from ...mapleio.character import Character


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
        self.user = user
        options = [
            discord.SelectOption(label=char['name'], value=str(i))
            for i, char in enumerate(user['chars'])
        ]
        text = 'Select a character...'
        super().__init__(placeholder=text, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.select = int(self.values[0])
        confirm = self.view.get_button('Confirm')
        confirm.disabled = False

        for opt in self.options:
            opt.default = str(self.view.select) == opt.value

        char = Character.from_json(self.user['chars'][self.view.select])
        self.view.embed.set_image(url=char.url())

        await interaction.response.edit_message(embed=self.view.embed, view=self.view)


class CharacterSelectView(discord.ui.View):
    def __init__(
            self,
            interaction: discord.Interaction,
            user: dict,
            embed: discord.Embed,
            timeout: int = 180
    ):
        super().__init__(timeout=timeout)
        self.orig_interaction = interaction
        self.embed = embed
        self.select = None  # select menu value
        self.response = None  # button value

        select = CharacterSelect(user)
        self.add_item(select)

    def get_button(self, label: str):
        buttons = [x for x in self.children if isinstance(x, discord.ui.Button)]
        return next((b for b in buttons if b.label == label), None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,
                       disabled=True, row=1)
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

    @discord.ui.button(label="Cancel", row=1)
    async def cancel(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
    ):
        self.select = None
        self.response = False
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        for comp in self.children:
            comp.disabled = True

        await self.orig_interaction.edit_original_response(view=self)


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


async def get_default_char(interaction: discord.Interaction):
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

    return Character.from_json(user['chars'][i])


async def get_char_index(
        interaction: discord.Interaction,
        user: dict,
        name: Optional[str] = None,
        title: Optional[str] = None,
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
    title: Optional[str]
        title displayed in embed prior to instructions
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

    # prompt if no name
    embed = discord.Embed(description=text, color=config.core.embed_color)
    embed.set_author(name=title)

    view = CharacterSelectView(interaction, user, embed)
    await interaction.edit_original_response(embed=embed, view=view)
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
