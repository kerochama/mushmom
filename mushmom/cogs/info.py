"""
Character profiles

"""
import discord

from discord.ext import commands
from io import BytesIO
from PIL import Image
from typing import Optional

from .. import config, mapleio
from .utils import errors, converters
from .resources import EMOJIS, ATTACHMENTS
from ..mapleio.character import Character


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def info(
            self,
            ctx: commands.Context,
            member: Optional[discord.Member] = None
    ) -> None:
        """
        Discord member profile

        Parameters
        ----------
        ctx: commands.Context
        member: Optional[discord.Member]
            member's profile to show. If not supplied, caller's profile

        """
        if not member:
            member = ctx.author

        embed = discord.Embed(
            title=f'{member.name}#{member.discriminator}',
            color=config.core.embed_color
        )
        mushhuh = self.bot.get_emoji_url(EMOJIS['mushhuh'])
        embed.set_author(name=f'{member.display_name}\'s Info',
                         icon_url=mushhuh)
        embed.set_thumbnail(url=member.display_avatar.url)

        user = await self.bot.db.get_user(member.id)
        if not user:
            attm = ATTACHMENTS['mushcharnotfound']
            not_found = self.bot.get_attachment_url(*attm)
            data = await self.bot.download(not_found, errors.DiscordIOError)

            # attach pfp
            pfp = await self.gen_profile_pic(data)
            filename = attm[-1]  # orig filename
            img = discord.File(fp=BytesIO(pfp), filename=filename)
            embed.set_image(url=f'attachment://{filename}')
            embed.set_footer(text='This member has no registered characters')
            await ctx.send(file=img, embed=embed)
        else:
            char = user['chars'][user['default']]
            char_info = {
                'name': char['name'],
                'game': 'MaplestoryM',
                'server': 'NA Inosys',
                'job': 'Bishop',
                'guild': 'Vital'
            }
            _fmt_info = [self._padded_str(f'**{k.title()}**: {v}')
                         for k, v in char_info.items()]
            embed.add_field(name='Active Character',
                            value='\n'.join(_fmt_info) + '\n\u200b')
            _fmt_fame = self._padded_str('\u2b50 9284', n=12)
            embed.add_field(name='Fame', value=_fmt_fame + '\n\u200b')

            # attach pfp
            data = await mapleio.api.get_sprite(
                Character.from_json(char), render_mode='FeetCenter')

            if not data:
                raise errors.MapleIOError

            pfp = await self.gen_profile_pic(data)
            filename = f'{char["name"]}.png'
            img = discord.File(fp=BytesIO(pfp), filename=filename)
            embed.set_image(url=f'attachment://{filename}')
            embed.set_footer(text='React with \U0001f44D \u200b to fame')
            await ctx.send(file=img, embed=embed)

    @staticmethod
    def _padded_str(text, n=30):
        s = list('\xa0' * n)
        s[:len(text)] = list(text)
        return ''.join(s)

    async def gen_profile_pic(
            self,
            data: bytes,
            bg: str = 'grassy_field',
            w=250,
            h=150
    ) -> bytes:
        """
        Create a profile picture with the char data and background specified

        Parameters
        ----------
        data: bytes
            character data (should be FeetCenter)
        bg: str
            discord attachment to lookup or url
        w: int
            width
        h: int
            height

        Returns
        -------
        bytes
            bytes of the generated profile picture

        """
        # get background
        try:
            url = self.bot.get_attachment_url(*ATTACHMENTS[bg])
        except KeyError:
            url = bg

        bg_data = await self.bot.download(url)
        bg = Image.open(BytesIO(bg_data)).convert('RGBA')
        w_bg, h_bg = bg.size

        # paste centered, 30px from bottom
        im = Image.open(BytesIO(data))
        w_im, h_im = im.size
        bg.paste(im, ((w_bg - w_im)//2, (h_bg - h_im//2 - 30)), mask=im)

        # crop to size
        out = bg.crop(((w_bg - w)//2, (h_bg - h), (w_bg + w)//2, h_bg))
        byte_arr = BytesIO()
        out.save(byte_arr, format='PNG')
        return byte_arr.getvalue()

    @commands.command(hidden=True)
    async def _set_info(
            self,
            ctx: commands.Context,
            *,
            options: converters.InfoFlags
    ) -> None:
        """
        Set character information displayed in profile

        Parameters
        ----------
        ctx: commands.Context
        options: converters.InfoFlags
            each of the fields that can be set

        """
        user = await self.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        char = user['chars'][user['default']]

        # go through all options
        for opt in vars(options):
            v = getattr(options, opt)
            if v is not None:
                char[opt] = v

        update = {'chars': user['chars']}  # passed by reference
        ret = await self.bot.db.set_user(ctx.author.id, update)

        if ret.acknowledged:
            await ctx.send(f'**{char["name"]}**\'s info was updated')
        else:
            raise errors.DataWriteError


def setup(bot):
    bot.add_cog(Info(bot))
