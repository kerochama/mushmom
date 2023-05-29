"""
Main commands for sending emotes

"""
import discord

from discord.ext import commands
from discord import app_commands

from typing import Optional
from io import BytesIO
from PIL import Image
from collections import namedtuple

from .. import mapleio, config
from .utils import io, errors

from discord.app_commands import Transform
from ..mapleio.character import Character
from ..mapleio.equip import Equip
from ..mapleio import imutils
from .utils.parameters import (
    CharacterTransformer, contains, autocomplete_chars
)

CUSTOM = (
    'teehee',
    'blink',
    'kek'
)

AccessoryInfo = namedtuple(
    'AccessoryInfo', 'itemid animated hide_face', defaults=(None, False, True)
)
FACE_ACCESSORIES = {
    'surprised': AccessoryInfo(1012429),
    'pout': AccessoryInfo(1012579),
    'grumpy': AccessoryInfo(1012621),
    'blank': AccessoryInfo(1012593),
    'grr': AccessoryInfo(1012685),
    'sideeye': AccessoryInfo(1012710),
    'sob': AccessoryInfo(1012711),
    'coy': AccessoryInfo(1012735),
    'shy': AccessoryInfo(1012737),
    'sulk': AccessoryInfo(1012721),
    # 'teary': AccessoryInfo(1012651, animated=True),
    # 'hearts': AccessoryInfo(1012740, animated=True),
    # 'crying': AccessoryInfo(1012761, animated=True)
}

# full list of emotes
EMOTE_LISTS = (
    mapleio.EXPRESSIONS,
    CUSTOM,
    FACE_ACCESSORIES.keys()
)
EMOTES = list(set([x for it in EMOTE_LISTS for x in it]))
EMOTES.sort()


class Mush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._mush_context_menu = app_commands.ContextMenu(
            name='Reply with Mush',
            callback=self.mush_context_menu
        )

        # non-command methods can be useful when called directly
        if isinstance(self.bot, discord.Client):
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

        # pass for tracking
        interaction.extras['emote'] = emote

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
            char: Character,
            min_width: int = config.core.min_emote_width
    ) -> discord.File:
        """
        Helper function to generate emote

        Parameters
        ----------
        emote: str
            the emote to send
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided
        min_width: int
            min width for emote

        Returns
        -------
        Optional[discord.File]
            the emote file

        """
        if emote not in EMOTES:
            msg = f'**{emote}** is not a valid emote'
            raise errors.BadArgument(msg, see_also=['list emotes'])

        # create emote
        if emote in CUSTOM:
            data = await getattr(self, emote)(char, min_width=min_width)
            ext = 'gif'
        elif emote in FACE_ACCESSORIES:
            data = await self._face_accessory_emote(
                char, *FACE_ACCESSORIES[emote], min_width=min_width
            )
            ext = 'gif' if FACE_ACCESSORIES[emote].animated else 'png'
        elif emote in mapleio.ANIMATED:
            data = await mapleio.api.get_animated_emote(
                char, expression=emote, min_width=min_width,
                session=self.bot.session
            )
            ext = 'gif'
        elif emote in mapleio.EXPRESSIONS:
            data = await mapleio.api.get_emote(
                char, expression=emote, min_width=min_width,
                session=self.bot.session
            )
            ext = 'png'

        if data:
            filename = f'{char.name or "char"}_{emote}.{ext}'
            return discord.File(fp=BytesIO(data), filename=filename)

    async def _face_accessory_emote(
            self,
            char: Character,
            itemid: int,
            animated: bool = False,
            hide_face: bool = True,
            min_width: int = config.core.min_emote_width
    ):
        """
        Create emote based off of face accessory

        Parameters
        ----------
        char: Character
            the character data
        itemid: int
            face accessory item id
        animated: bool
            whether or not the accessory is animated
        hide_face: bool
            whether or not orig face should be hidden
        min_width: int
            min width for emote

        Returns
        -------
        bytes
            image data

        """
        coro = (mapleio.api.get_animated_emote if animated
                else mapleio.api.get_emote)
        face_acc = Equip(itemid, char.version, char.region)

        # args
        data = await coro(
            char,
            expression='default',
            hide=['Face'] if hide_face else None,
            replace=[face_acc],
            min_width=min_width,
            session=self.bot.session
        )

        return data

    async def teehee(
            self,
            char: Character,
            min_width: int = config.core.min_emote_width
    ) -> bytes:
        """
        Teehee emote from cheers & hand from stab01

        Parameters
        ----------
        char: Character
            the character data
        min_width: int
            min width for emote

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
            frames.append(imutils.min_width(frame, min_width))

        byte_arr = BytesIO()
        frames[0].save(byte_arr, format='GIF', save_all=True, loop=0,
                       append_images=frames[1:], duration=100, disposal=2)
        return byte_arr.getvalue()

    async def blink(
            self,
            char: Character,
            min_width: int = config.core.min_emote_width
    ):
        """
        Custom duration for blink. Overwrites regular

        Parameters
        ----------
        char: Character
            the character data
        min_width: int
            min width for emote

        Returns
        -------
        bytes
            image data

        """
        data = await mapleio.api.get_animated_emote(
            char, expression='blink', min_width=min_width,
            session=self.bot.session
        )
        _blink = Image.open(BytesIO(data))

        # assemble frames
        frames = []
        for i in range(_blink.n_frames):
            _blink.seek(i)
            im = _blink.convert('RGBA')
            frames.append(im)

        open, closed, half, _ = frames
        frames = [open, closed, half, open, closed, half]
        duration = [2000, 10, 120, 10, 10, 10]

        byte_arr = BytesIO()
        frames[0].save(byte_arr, format='GIF', save_all=True, loop=0,
                       append_images=frames[1:], duration=duration, disposal=2)
        return byte_arr.getvalue()

    async def kek(
            self,
            char: Character,
            min_width: int = config.core.min_emote_width
    ):
        """
        Kek emote using Ushishishi Face

        Parameters
        ----------
        char: Character
            the character data
        min_width: int
            min width for emote

        Returns
        -------
        bytes
            image data

        """
        acc = AccessoryInfo(1012662)
        data = await self._face_accessory_emote(
            char, *acc, min_width=min_width
        )
        base = Image.open(BytesIO(data))
        clean = imutils.thresh_alpha(base, 64)
        shift = Image.new('RGBA', clean.size, (0,)*4)
        shift.paste(clean, (0, 2), mask=clean)

        # make gif
        frames = [clean, shift]
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