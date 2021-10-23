"""
Character profiles

"""
import discord
import asyncio

from discord.ext import commands
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Iterable

from .. import config, mapleio
from .utils import errors, converters
from .resources import EMOJIS, ATTACHMENTS
from ..mapleio.character import Character


UTC = timezone.utc
NYC = ZoneInfo('America/New_York')  # new york timezone

def utc(ts):
    return ts.replace(tzinfo=UTC)

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

        # get user info
        user = await self.bot.db.get_user(member.id)

        if not user:
            user, char = {}
        else:
            if not user['chars']:
                char = {}
            else:
                char = user['chars'][user['default']]

        char_info = {
            'name': char.get('name') or '-',
            'job': char.get('job') or '-',
            'game': char.get('game') or '-',
            'server': char.get('server') or '-',
            'guild': char.get('guild') or '-'
        }
        fame = user.get('fame', 0)

        # format info
        _fmt_info = [self._padded_str(f'> **{k.title()}**: {v}')
                     for k, v in char_info.items()]
        embed.add_field(name='Active Character',
                        value='\n'.join(_fmt_info) + '\n\u200b')
        _fmt_fame = self._padded_str(f'\u2b50 {fame}', n=12)
        embed.add_field(name='Fame', value=_fmt_fame + '\n\u200b')

        # send placeholder pfp in 3 seconds
        temp = ATTACHMENTS['pfp_loading']
        pfp_temp = self.bot.get_attachment_url(*temp)
        embed.set_image(url=pfp_temp)
        embed.set_footer(text='Still loading profile picture')
        temp_send_task = self.bot.loop.create_task(
            self._delayed_send(ctx, embed=embed)
        )

        # get real pfp
        if not char:
            attm = ATTACHMENTS['mushcharnotfound']
            not_found = self.bot.get_attachment_url(*attm)
            filename = attm[-1]  # orig filename

            try:
                data = await self.bot.download(not_found, errors.DiscordIOError)
            except errors.DiscordIOError:
                data = None

            embed.set_footer(text='This member has no registered characters')
        else:
            filename = f'{char.get("name") or "char"}.png'
            data = await mapleio.api.get_sprite(
                Character.from_json(char), render_mode='FeetCenter')

            embed.set_footer(text='React with \U0001f44D \u200b to fame')

        if data:  # successful get
            pfp_data = await self.gen_profile_pic(data)
            pfp = discord.File(fp=BytesIO(pfp_data), filename=filename)
        else:
            pfp = None

        # cancel if not yet sent, else edit
        if not temp_send_task.done():
            temp_send_task.cancel()

            if pfp:
                embed.set_image(url=f'attachment://{filename}')
                await ctx.send(file=pfp, embed=embed)
            else:
                pfp_poo = self.bot.get_attachment_url(*ATTACHMENTS['pfp_poo'])
                embed.set_image(url=pfp_poo)
                await ctx.send(embed=embed)
        else:
            msg = temp_send_task.result()

            # default fail
            pfp_poo = self.bot.get_attachment_url(*ATTACHMENTS['pfp_poo'])
            embed.set_image(url=pfp_poo)

            if pfp:  # upload to another channel and get the attachment url
                uploads = config.discord.uploads
                channel = (self.bot.get_channel(uploads)
                           or await self.bot.fetch_channel(uploads))
                try:
                    _up = await channel.send(file=pfp)
                    embed.set_image(url=_up.attachments[0].url)
                except Exception:  # just send poo
                    pass

            await msg.edit(embed=embed)

    @staticmethod
    async def _delayed_send(ctx, delay=3, **kwargs):
        await asyncio.sleep(delay)
        return await ctx.send(**kwargs)

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

    async def _fame(
            self,
            ctx: commands.Context,
            member: discord.Member,
            amt: int = 1,
            send_confirm: bool = True
    ) -> None:
        """
        Internal function for adding fame (or defame). Bot owner
        will circumvent all checks.

        Parameters
        ----------
        ctx: commands.Context
        member: discord.Member
            the member to fame
        amt: int
            the amount to fame. can be negative
        send_confirm: bool
            whether or not to send message confirming update

        """
        if member.id == ctx.author.id:
            raise errors.SelfFameError

        target = await self.bot.db.get_user(member.id, track=False)
        if not target:
            raise errors.DataNotFound

        update = {'fame': target['fame'] + amt}

        # owner can fame whenever
        if ctx.author.id == self.bot.owner_id:
            await self.bot.db.set_user(member.id, update)
        else:
            # regular user
            user = await self.bot.db.get_user(ctx.author.id)
            if not user:
                ret = await self.bot.db.add_user(ctx.author.id)
                if not ret.acknowledged:
                    raise errors.DataWriteError
                else:
                    user = await self.bot.db.get_user(ctx.author.id)

            # check if already famed or max fame reached
            fame_log = FameLog(user['fame_log'])

            if member.id in fame_log:
                raise errors.AlreadyFamedError

            # negative amount is a defame. cnt is separate for each
            cnt = len(fame_log.fames() if amt > 1 else fame_log.defames())

            if cnt >= config.core.max_fame_limit:
                raise errors.MaxFamesReached

            # add fame
            ret = await self.bot.db.set_user(member.id, update)

            if ret.acknowledged:
                if amt > 0:
                    fame_log.add_fame(member.id)
                else:
                    fame_log.add_defame(member.id)

                await self.bot.db.set_user(ctx.author.id, {'fame_log': fame_log})
            else:
                raise errors.DataWriteError

        if send_confirm:
            verb = f'{"de" if amt < 0 else ""}famed'
            await ctx.send(f'You {verb} **{member.display_name}**')

    @commands.command()
    async def fame(
            self,
            ctx: commands.Context,
            member: discord.Member
    ) -> None:
        """
        Fame someone (by account). You can only fame up to 10 people a
        day, which will reset at midnight eastern time.

        Parameters
        ----------
        ctx: commands.Context
        member: discord.Member
            the member to fame

        """
        await self._fame(ctx, member, 1)

    @commands.command()
    async def defame(
            self,
            ctx: commands.Context,
            member: discord.Member
    ) -> None:
        """
        Defame someone (by account). You can only defame up to 10
        people a day, which will reset at midnight eastern time.

        Parameters
        ----------
        ctx: commands.Context
        member: discord.Member
            the member to defame

        """
        await self._fame(ctx, member, -1)

    @commands.command()
    async def test(self, ctx):
        print(self.bot.owner_id)

class FameLog(list):
    """
    List of tuple[int, int, datetime], which is userid, amount,
    and timestamp. timestamp is output of datetime.utcnow()
    (i.e. tz unaware, but utc)

    Records that are not from today are removed on init

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utcnow = utc(datetime.utcnow())
        today = utcnow.astimezone(NYC).date()

        # clean old records. iterate over copy
        for fame in self[:]:
            uid, amt, ts = fame
            if utc(ts).astimezone(NYC).date() != today:
                self.remove(fame)

    def fames(self):
        return FameLog(filter(lambda x: x[1]>0, self))  # x[1] is amt

    def defames(self):
        return FameLog(filter(lambda x: x[1]<0, self))  # x[1] is amt

    def __contains__(self, uid):
        for fame in self:
            if fame[0] == uid:
                return True

        return False

    def add_fame(self, uid):
        self.append((uid, 1, datetime.utcnow()))

    def add_defame(self, uid):
        self.append((uid, -1, datetime.utcnow()))


def setup(bot):
    bot.add_cog(Info(bot))
