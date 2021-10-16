"""
Character actions

"""
import discord

from discord.ext import commands
from types import SimpleNamespace
from PIL import Image, ImageOps
from io import BytesIO
from itertools import cycle
from typing import Optional, Union, Any, Iterable

from .. import config
from .utils import converters, errors, prompts
from ..mapleio import api
from ..mapleio.character import Character
from ..mapleio.equip import Equip


class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def action(
            self,
            ctx: commands.Context,
            char: Character,
            char_args: dict[str, Any],
            obj: discord.Member,  # object as in object of verb
            obj_args: dict[str, Any],
            pad: int = 40,
    ) -> None:
        """
        Logic for putting two images side by side

        Parameters
        ----------
        ctx: commands.Context
        char: Character
            the command caller
        char_args: dict[str, Any]
            args to pass to api call
        obj: discord.Member
            the recipient of action
        obj_args: dict[str, Any]
            args to pass to api call if has char
        pad: int
            pixels between char navels

        """
        session = self.bot.session

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(config.emojis.mushloading) or '\u23f3'
        react_task = self.bot.loop.create_task(
            self.bot.add_delayed_reaction(ctx, emoji)
        )

        # get images to combine
        _char = await api.split_layers(
            char, render_mode='FeetCenter', session=session, **char_args)

        try:
            _ctx = SimpleNamespace(bot=self.bot, author=obj)  # fake ctx
            obj_char = await converters.default_char(_ctx)
            _obj = await api.split_layers(
                obj_char, render_mode='FeetCenter', remove=['Weapon'],
                session=session, **obj_args)
        except errors.NoMoreItems:  # use pfp
            pfp = await self.process_pfp(obj, config.core.default_pfp_size)
            _obj = (pfp, pfp)

        react_task.cancel()  # no need to send if it gets here first
        await ctx.message.clear_reactions()

        if not _char or not _obj:
            raise errors.MapleIOError

        im1 = [ImageOps.mirror(Image.open(BytesIO(x))) for x in _char]
        im2 = [Image.open(BytesIO(x)) for x in _obj]
        res = await self.merge(im1, im2, pad)

        # trim blank space
        res = res.crop(res.getbbox())
        byte_arr = BytesIO()
        res.save(byte_arr, format='PNG')

        # send
        filename = f'stab.png'
        img = discord.File(fp=BytesIO(byte_arr.getvalue()), filename=filename)
        await ctx.send(file=img)

    async def merge(
            self,
            im1: Union[Image.Image, Iterable[Image.Image]],
            im2: Union[Image.Image, Iterable[Image.Image]],
            pad: int = 40
    ) -> Image.Image:
        """Merge into one image with mid widths separated by pad. If
        Iterable passed then alternate pasting layers"""
        if isinstance(im1, Image.Image):
            im1 = [im1]

        if isinstance(im2, Image.Image):
            im2 = [im2]

        n = max(len(im1), len(im2))
        cyc1, cyc2 = cycle(reversed(im1)), cycle(reversed(im2))

        # get output size
        # handle one image much longer than the other
        a, b = im1[0], im2[0]
        w = max(a.width, b.width, sum((a.width, b.width))//2 + pad)
        h = max(a.height, b.height)

        # generate output image
        res = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for i in range(n):
            _a, _b = next(cyc1), next(cyc2)
            res.paste(_b, (w-_b.width, (h-_b.height)//2), mask=_b)
            res.paste(_a, (0, (h-_a.height)//2), mask=_a)

        return res

    async def process_pfp(self, member: discord.Member, width: int) -> bytes:
        """Resize to specified width and double height to mimic sprite
        render_mode=FeetCentered"""
        async with self.bot.session.get(member.display_avatar.url) as r:
            if r.status == 200:
                pfp = Image.open(BytesIO(await r.read()))
                pfp = pfp.convert(mode='RGBA')
                pfp.thumbnail((width, width), Image.ANTIALIAS)
                out = Image.new('RGBA', (width, width * 2), (0, 0, 0, 0))
                out.paste(pfp, (0, 0), mask=pfp)
            else:
                raise errors.DiscordIOError

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
        data = await api.get_sprite(
            char, pose=pose, frame=frame, render_mode='centered',
            remove=['Cape'], session=self.bot.session)
        w, _ = Image.open(BytesIO(data)).size
        return w//2

    @commands.command()
    async def stab(
            self,
            ctx: commands.Context,
            member: discord.Member,
            weapon_id: Optional[int] = 1542069,  # pearl maple katana
            pad: Optional[int] = 16,
            *,
            options: converters.ImgFlags
    ) -> None:
        """
        Stab another user's character. If no character exists, stab
        their profile picture

        Parameters
        ----------
        ctx: commands.Context
        member: discord.Member
            the user to stab
        weapon_id: Optional[int]
            the weapon with which to stab
        pad: Optional[int]
            extra distance to add to weapon width
        options: converters.ImgFlags
            --char, -c: character to use

        """
        char = options.char
        wep = Equip(weapon_id, char.version, char.region)
        wep_width = await self.weapon_width(weapon_id, pose='stabO1', frame=1)
        _pad = wep_width + pad

        char = options.char
        char_args = {'pose': 'stabO1', 'frame': 1, 'replace': [wep]}
        obj_args = {'emotion': 'despair'}

        await self.action(ctx, char, char_args, member, obj_args, pad=_pad)

    @commands.command()
    async def slap(
            self,
            ctx: commands.Context,
            member: discord.Member,
            pad: Optional[int] = 16,
            *,
            options: converters.ImgFlags
    ) -> None:
        """
        Slap another user's character. If no character exists, slap
        their profile picture

        Parameters
        ----------
        ctx: commands.Context
        member: discord.Member
            the user to stab
        pad: Optional[int]
            extra distance to add to weapon width
        options: converters.ImgFlags
            --char, -c: character to use

        """
        char = options.char
        wep = Equip(1702554, char.version, char.region)  # scary huge hand
        _pad = 64 + pad  # hard coded wep width

        char_args = {'pose': 'swingO1', 'frame': 2, 'replace': [wep]}
        obj_args = {'emotion': 'pain'}

        await self.action(ctx, char, char_args, member, obj_args, pad=_pad)


def setup(bot):
    bot.add_cog(Actions(bot))
