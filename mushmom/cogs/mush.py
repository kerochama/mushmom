"""
Main commands for sending emotes

"""
import discord

from discord.ext import commands
from discord import app_commands

from typing import Optional
from io import BytesIO
from PIL import Image

from .. import mapleio, config
from .utils import io, errors

from discord.app_commands import Transform
from ..mapleio.character import Character
from ..mapleio import imutils
from .utils.parameters import (
    CharacterTransformer, contains, autocomplete_chars
)

CUSTOM = (
    'teehee',
)

FACE_ACCESSORIES = {}

# full list of emotes
EMOTE_LISTS = (
    mapleio.EXPRESSIONS,
    CUSTOM,
    FACE_ACCESSORIES.keys()
)
EMOTES = [x for it in EMOTE_LISTS for x in it]


class Mush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._mush_context_menu = app_commands.ContextMenu(
            name='Reply with Mush',
            callback=self.mush_context_menu
        )
        self.bot.tree.add_command(self._mush_context_menu)

    @app_commands.command()
    @app_commands.autocomplete(emote=contains(EMOTES),
                               char=autocomplete_chars)
    async def mush(
            self,
            interaction: discord.Interaction,
            emote: str,
            char: Optional[Transform[Character, CharacterTransformer]] = None
    ) -> None:
        """
        Send maple emotes of your character

        Parameters
        ----------
        interaction: discord.Interaction,
        emote: str
            the emote to send
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided

        """
        await self.bot.defer(interaction)

        # create emote
        char = char or await io.get_default_char(interaction)
        img = await self._generate_emote(emote, char)

        if img:
            if await self.bot.send_as_author(interaction, file=img):
                await self.bot.followup(
                    interaction, content='Emote was sent', delete_after=0
                )  # delete immediately
        else:
            raise errors.MapleIOError

    async def mush_context_menu(
            self,
            interaction: discord.Interaction,
            message: discord.Message
    ) -> None:
        """
        Enter emote name and reply to message by creating thread. Switch to
        replying if Webhooks become able to

        Parameters
        ----------
        interaction: discord.Interaction
        message: discord.Message

        """
        modal = EmoteSelectModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        if not modal.submit:  # cancelled
            return

        # create emote
        emote = modal.emote.value
        char = await io.get_default_char(interaction)  # always use default
        img = await self._generate_emote(emote, char)

        # create thread
        if img:
            name = (
                message.clean_content if len(message.clean_content) <= 30
                else message.clean_content[:30] + '...'
            )
            thread = await message.create_thread(
                name=name, auto_archive_duration=60, reason='mush reply'
            )
            kwargs = {'file': img, 'thread': thread}
            if await self.bot.send_as_author(interaction, **kwargs):
                await self.bot.followup(
                    modal.submit, content='Emote was sent', delete_after=0
                )  # delete immediately
        else:
            raise errors.MapleIOError

    async def _generate_emote(
            self,
            emote: str,
            char: Character
    ) -> discord.File:
        """
        Helper function to generate emote

        Parameters
        ----------
        emote: str
            the emote to send
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided

        Returns
        -------
        Optional[discord.File]
            the emote file

        """
        if emote not in EMOTES:
            msg = f'**{emote}** is not a valid emote'
            raise errors.BadArgument(msg, see_also=['list emotes'])

        # create emote
        if emote in mapleio.ANIMATED:
            data = await mapleio.api.get_animated_emote(
                char, expression=emote, min_width=300, session=self.bot.session
            )
            ext = 'gif'
        elif emote in mapleio.EXPRESSIONS:
            data = await mapleio.api.get_emote(
                char, expression=emote, min_width=300, session=self.bot.session
            )
            ext = 'png'
        elif emote in CUSTOM:
            data = await getattr(self, emote)(char)
            ext = 'gif'

        if data:
            filename = f'{char.name or "char"}_{emote}.{ext}'
            return discord.File(fp=BytesIO(data), filename=filename)

    async def teehee(self, char: Character) -> bytes:
        """
        Teehee emote from cheers & hand from stab01

        Parameters
        ----------
        char: Character
            the character data

        Returns
        -------
        bytes
            image data

        """
        arm_offset_x, arm_height = 1, 13
        pad = 12  # feet center

        # api calls
        _base = await mapleio.api.get_sprite(
            char, pose='stand1', expression='cheers', session=self.bot.session,
            remove=['Cape', 'Weapon', 'Shoes'], render_mode='FeetCenter'
        )
        _hand = await mapleio.api.get_sprite(
            char, pose='stabO1', frame=1, session=self.bot.session,
            hide=['Head'], keep=['Overall', 'Top', 'Glove']
        )

        # format base
        base = Image.open(BytesIO(_base))
        w, h = base.size
        body_height = config.mapleio.body_height - pad
        base = base.crop((0, 0, w, h//2 - body_height))
        bbox = imutils.get_bbox(base)
        base = base.crop(bbox)
        center = w//2 - bbox[0]  # shift based on bbox

        # trim to just the hand
        hand = Image.open(BytesIO(_hand)).rotate(270)
        hand_roi = hand.crop(imutils.get_bbox(hand))
        hand_roi = hand_roi.crop((0, 0, hand_roi.width, arm_height))
        hand = hand_roi.crop(imutils.get_bbox(hand_roi))

        # create frames
        frames = []
        for pos in [(0, 0), (0, 1)]:  # shift frame 1 down 1 pixel
            frame = Image.new('RGBA', base.size, (0,)*4)
            frame.paste(base, pos, mask=base)
            x, y = center - hand.width + arm_offset_x, base.height - arm_height
            frame.paste(hand, (x, y), mask=hand)
            frame = imutils.thresh_alpha(frame, 64)
            frames.append(imutils.min_width(frame, 300))

        byte_arr = BytesIO()
        frames[0].save(byte_arr, format='GIF', save_all=True, loop=0,
                       append_images=frames[1:], duration=100, disposal=2)
        return byte_arr.getvalue()


class EmoteSelectModal(discord.ui.Modal, title='Select Emote'):
    def __init__(self):
        super().__init__()
        self.submit = None

        # items
        self.emote = discord.ui.TextInput(
            label='Emote',
            placeholder="Enter emote name...",
            max_length=30,
        )

        static = [emote for emote in mapleio.EXPRESSIONS
                  if emote not in mapleio.ANIMATED]
        animated = mapleio.ANIMATED
        text = (f'Animated:\n{", ".join(animated)}\n\n'
                f'Static:\n{", ".join(static)}')

        self.options = discord.ui.TextInput(
            label='Options',
            placeholder='o.o',
            default=text,
            style=discord.TextStyle.long,
            required=False
        )

        # add inputs
        self.add_item(self.emote)
        self.add_item(self.options)

    async def on_submit(self, interaction: discord.Interaction):
        self.submit = interaction
        await interaction.response.defer(thinking=True, ephemeral=True)
        self.stop()


async def setup(bot):
    await bot.add_cog(Mush(bot))