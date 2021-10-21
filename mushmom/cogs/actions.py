"""
Character actions

"""
import discord
import numpy as np
import datetime

from discord.ext import commands
from types import SimpleNamespace
from PIL import Image, ImageOps, ImageColor
from io import BytesIO
from itertools import cycle
from typing import Optional, Union, Any, Iterable

from .. import config, mapleio
from .utils import converters, errors
from .resources import EMOJIS
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
            duration: Union[int, Iterable[int]] = 100,
            title: str = '',
            desc: str = ''
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
        duration: Union[int, Iterable[int]]
            milliseconds
        title: str
            title for embed
        desc: str
            description for embed

        """
        session = self.bot.session

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(EMOJIS['mushloading']) or '\u23f3'
        react_task = self.bot.loop.create_task(
            self.bot.add_delayed_reaction(ctx, emoji)
        )

        # get frames and make them all the same size
        _frames = await mapleio.api.get_frames(
            char, render_mode='FeetCenter', session=session, **char_args)

        if not _frames:
            raise errors.MapleIOError

        frames = [Image.open(BytesIO(frame)) for frame in _frames]
        sizes = [f.size for f in frames]
        w, h = [max(dim) for dim in zip(*sizes)]

        try:
            _ctx = SimpleNamespace(bot=self.bot, author=obj)  # fake ctx
            obj_char = await converters.default_char(_ctx)
            data = await mapleio.api.get_sprite(
                obj_char, render_mode='FeetCenter', remove=['Weapon', 'Cape'],
                session=session, **obj_args)
            _obj = Image.open(BytesIO(data))
            w_obj, h_obj = _obj.size  # width of orig (centered)

            if not data:
                raise errors.MapleIOError

        except errors.NoMoreItems:  # use pfp
            data = await self.process_pfp(obj, config.core.default_pfp_size)
            _obj = Image.open(BytesIO(data))
            w_obj, h_obj = _obj.getbbox()[2:]

            if not data:
                raise errors.DiscordIOError

        react_task.cancel()  # no need to send if it gets here first
        await ctx.message.clear_reactions()

        _hex = format(config.core.embed_bg_color, "x")
        bgcolor = ImageColor.getcolor(f'#{_hex}', 'RGBA')

        merged = []
        for f in frames:
            new = Image.new('RGBA', (w, h), bgcolor)
            flip = ImageOps.mirror(f)
            new.paste(flip, ((w-f.width)//2, (h-f.height)//2), mask=flip)
            _f = self.merge(new, _obj, pad, z_order=-1, bgcolor=bgcolor)
            merged.append(_f)

        # trim
        bbox = self.getbbox(merged, ignore=bgcolor)
        merged = [f.crop(bbox) for f in merged]

        # ensure somewhat symmetrical
        w_diff = (w - w_obj)//2
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
        filename = f'{ctx.command.name}.gif'
        img = discord.File(fp=BytesIO(byte_arr.getvalue()), filename=filename)

        embed = discord.Embed(description=desc,
                              color=config.core.embed_color)
        embed.set_author(name=title)
        embed.set_image(url=f'attachment://{filename}')
        embed.timestamp = datetime.datetime.utcnow()
        icon = ctx.author.display_avatar.url
        embed.set_footer(text=ctx.author.display_name, icon_url=icon)
        await ctx.send(file=img, embed=embed)

    @staticmethod
    def merge(
            im1: Union[Image.Image, Iterable[Image.Image]],
            im2: Union[Image.Image, Iterable[Image.Image]],
            pad: int = 40,
            z_order: int = 1,  # -1 = im2 on top of im1
            bgcolor: tuple[int] = (0, 0, 0, 0)
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
        res = Image.new('RGBA', (w, h), bgcolor)
        for i in range(n):
            l, r = next(cyc1), next(cyc2)
            layers = [  # first is underneath
                (r, (w-r.width, (h-r.height)//2)),
                (l, (0, (h-l.height)//2))
            ]

            for im, pos in (layers if z_order == 1 else reversed(layers)):
                res.paste(im, pos, mask=im)

        return res

    @staticmethod
    def getbbox(
            im: Union[Iterable[Image.Image], Image.Image],
            ignore: Optional[tuple[int, int, int, int]]= None,
    ) -> tuple[int, int, int, int]:
        """Make color transparent and get bounding box for all frames"""
        if isinstance(im, Image.Image):
            im = [im]

        bboxes = []
        for frame in im:
            if ignore:
                data = np.array(frame)
                r, g, b, a = data.T  # transpose
                _r, _g, _b, _a = ignore
                mask = (r == _r) & (g == _g) & (b == _b) & (a == _a)
                data[:, :, :4][mask.T] = (0, 0, 0, 0)  # untranspose mask
                bboxes.append(Image.fromarray(data).getbbox())
            else:
                bboxes.append(frame.getbbox())

        T = list(zip(*bboxes))  # transpose
        bbox = [min(x) for x in T[:2]] + [max(x) for x in T[2:]]
        return tuple(bbox)

    async def process_pfp(self, member: discord.Member, width: int) -> bytes:
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

    @commands.command()
    async def stab(
            self,
            ctx: commands.Context,
            member: discord.Member,
            weapon_id: Optional[int] = 1332007,  # fruit knife
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
        # see gif. frame one in gif split between 0 and 2 (gif only 2 frames)
        dur = [175, 450, 175]

        char = options.char
        char_args = {'pose': 'stabO1', 'emotion': 'default', 'replace': [wep]}
        obj_args = {'pose': 'stand1', 'emotion': 'despair'}

        msg = f'{member.display_name} has been stabbed'
        await self.action(ctx, char, char_args, member, obj_args, pad=_pad,
                          duration=dur, title=msg, desc='_Stab! Stab! Stab!_')

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
        # see gif. frame one in gif split between 0 and 4 (gif only 4 frames)
        dur = [100, 100, 100, 300, 100]

        char_args = {'pose': 'swingOF', 'emotion': 'default', 'replace': [wep]}
        obj_args = {'pose': 'stand1', 'emotion': 'pain'}

        msg = f'{member.display_name} has been slapped'
        await self.action(ctx, char, char_args, member, obj_args, pad=_pad,
                          duration=dur, title=msg, desc='_Pow! Pow! Pow!_')


def setup(bot):
    bot.add_cog(Actions(bot))
