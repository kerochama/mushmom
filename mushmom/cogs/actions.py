"""
Character actions

"""
import discord

from discord import app_commands
from discord.ext import commands
from discord.app_commands import Transform

from types import SimpleNamespace
from PIL import Image, ImageOps, ImageColor
from io import BytesIO
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union, Any, Iterable

from .. import config, mapleio
from .utils import converters, errors, io
from .utils.parameters import autocomplete_chars, CharacterTransformer
from ..mapleio import imutils
from ..mapleio.character import Character
from ..mapleio.equip import Equip


UTC = timezone.utc
NYC = ZoneInfo('America/New_York')  # new york timezone


class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def action(
            self,
            interaction: discord.Interaction,
            char: Character,
            char_args: dict[str, Any],
            target: discord.Member,
            target_args: dict[str, Any],
            pad: int = 40,
            duration: Union[int, Iterable[int]] = 100,
            msg: str = '',
            desc: str = ''
    ) -> None:
        """
        Logic for putting two images side by side

        Parameters
        ----------
        interaction: discord.Interaction
        char: Character
            the command caller
        char_args: dict[str, Any]
            args to pass to api call
        target: discord.Member
            the recipient of action
        target_args: dict[str, Any]
            args to pass to api call if has char
        pad: int
            pixels between char navels
        duration: Union[int, Iterable[int]]
            milliseconds
        msg: str
            text for content
        desc: str
            description for embed

        """
        defer = f'Preparing to {interaction.command.name} {target.mention}'
        await self.bot.defer(interaction, defer, ephemeral=False)
        session = self.bot.session

        # get frames and make them all the same size
        _frames = await mapleio.api.get_frames(
            char, render_mode='FeetCenter', session=session, **char_args)

        if not _frames:
            raise errors.MapleIOError

        frames = [Image.open(BytesIO(frame)) for frame in _frames]
        sizes = [f.size for f in frames]
        w, h = [max(dim) for dim in zip(*sizes)]

        try:  # use fake interaction to get char
            _interaction = SimpleNamespace(client=self.bot, user=target)
            target_char = await io.get_default_char(_interaction)
            data = await mapleio.api.get_sprite(
                target_char, session=session, render_mode='FeetCenter',
                remove=['Weapon', 'Cape'], **target_args
            )
            _target = Image.open(BytesIO(data))
            w_target, h_target = _target.size  # width of orig (centered)

            if not data:
                raise errors.MapleIOError

        except errors.NoCharacters:  # use pfp if target not registered
            data = await self.render_pfp(target, config.core.default_pfp_size)
            _target = Image.open(BytesIO(data))
            w_target, h_target = _target.getbbox()[2:]

            if not data:
                raise errors.DiscordIOError

        _hex = format(config.core.embed_bg_color, "x")
        bgcolor = ImageColor.getcolor(f'#{_hex}', 'RGBA')

        merged = []
        for f in frames:
            new = Image.new('RGBA', (w, h), bgcolor)
            flip = ImageOps.mirror(f)
            new.paste(flip, ((w-f.width)//2, (h-f.height)//2), mask=flip)
            _f = imutils.merge(new, _target, pad, z_order=-1, bgcolor=bgcolor)
            merged.append(_f)

        # trim
        bbox = imutils.get_bbox(merged, ignore=bgcolor)
        merged = [f.crop(bbox) for f in merged]

        # ensure somewhat symmetrical
        w_diff = (w - w_target)//2
        final = []
        for f in merged:
            new = Image.new('RGBA', (f.width + abs(w_diff), f.height), bgcolor)
            new.paste(f, (0 if w_diff > 0 else abs(w_diff), 0), mask=f)
            final.append(new)

        # save
        byte_arr = BytesIO()
        final[0].save(byte_arr, format='GIF', save_all=True,
                      append_images=final[1:], duration=duration, loop=0)

        # send embed
        filename = f'{interaction.command.name}.gif'
        img = discord.File(fp=BytesIO(byte_arr.getvalue()), filename=filename)

        embed = discord.Embed(description=desc,
                              color=config.core.embed_color)
        embed.set_image(url=f'attachment://{filename}')
        embed.timestamp = datetime.utcnow().replace(tzinfo=UTC).astimezone(NYC)
        icon = interaction.user.display_avatar.url
        embed.set_footer(text=interaction.user.display_name, icon_url=icon)

        # send message. Can't ping in embed
        await self.bot.followup(interaction, content=msg, embed=embed,
                                attachments=[img])

    async def render_pfp(self, member: discord.Member, width: int) -> bytes:
        """Resize to specified width and double height and adds
        horizontal spacing to mimic sprite render_mode=FeetCentered"""
        url = member.display_avatar.url
        data = await self.bot.download(url, errors.DiscordIOError)
        pfp = Image.open(BytesIO(data)).convert(mode='RGBA')
        pfp.thumbnail((width, width), Image.ANTIALIAS)

        # create output
        out = Image.new('RGBA', (int(width * 1.5), width * 2), (0,)*4)
        out.paste(pfp, (width//2, 0), mask=pfp)
        byte_arr = BytesIO()
        out.save(byte_arr, format='PNG')
        return byte_arr.getvalue()

    async def weapon_width(
            self,
            weapon_id: int,
            pose: str,
            frame: Union[int, str]
    ) -> int:
        """Get the distance between sprite center and tip of weapon"""
        char = Character()  # nekid
        char.equips.append(Equip(weapon_id, char.version))
        data = await mapleio.api.get_sprite(
            char, pose=pose, frame=frame, render_mode='centered',
            remove=['Cape'], session=self.bot.session)
        w, _ = Image.open(BytesIO(data)).size
        return w//2

    @app_commands.command()
    @app_commands.autocomplete(char=autocomplete_chars)
    async def stab(
            self,
            interaction: discord.Interaction,
            member: discord.Member,
            char: Optional[Transform[Character, CharacterTransformer]] = None,
            weapon_id: Optional[int] = 1332007,  # fruit knife
    ) -> None:
        """
        Stab another user's character. If no character exists, stab
        their profile picture

        Parameters
        ----------
        interaction: discord.Interaction
        member: discord.Member
            the user to stab
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided
        weapon_id: Optional[int]
            the weapon with which to stab. Use ID from maplestory.io

        """
        pad = 16  # default padding. could be an argument, but hardcoding
        char = char or await io.get_default_char(interaction)

        wep = Equip(weapon_id, char.version, char.region)
        wep_width = await self.weapon_width(weapon_id, pose='stabO1', frame=1)
        _pad = wep_width + pad
        # see gif. frame one in gif split between 0 and 2 (gif only 2 frames)
        dur = [175, 450, 175]

        char_args = {
            'pose': 'stabO1',
            'expression': 'default',
            'replace': [wep]
        }
        target_args = {'pose': 'stand1', 'expression': 'despair'}

        msg = f'{member.mention} has been stabbed'
        desc = '_Stab! Stab! Stab!_'
        await self.action(interaction, char, char_args, member, target_args,
                          pad=_pad, duration=dur, msg=msg, desc=desc)

    @app_commands.command()
    @app_commands.autocomplete(char=autocomplete_chars)
    async def slap(
            self,
            interaction: discord.Interaction,
            member: discord.Member,
            char: Optional[Transform[Character, CharacterTransformer]] = None
    ) -> None:
        """
        Slap another user's character. If no character exists, slap
        their profile picture

        Parameters
        ----------
        interaction: discord.Interaction
        member: discord.Member
            the user to slap
        char: Optional[Transform[Character, CharacterTransformer]]
            character to use. Default char if not provided

        """
        pad = 16  # default padding. could be an argument, but hardcoding
        char = char or await io.get_default_char(interaction)

        wep = Equip(1702554, char.version, char.region)  # scary huge hand
        _pad = 64 + pad  # hard coded wep width
        # see gif. frame one in gif split between 0 and 4 (gif only 4 frames)
        dur = [75, 75, 175, 75]

        char_args = {
            'pose': 'swingO3',
            'expression': 'default',
            'replace': [wep]
        }
        target_args = {'pose': 'stand1', 'expression': 'pain'}

        msg = f'{member.mention} has been slapped'
        desc = '_Bam! Bam! Bam!_'
        await self.action(interaction, char, char_args, member, target_args,
                          pad=_pad, duration=dur, msg=msg, desc=desc)


async def setup(bot):
    await bot.add_cog(Actions(bot))
