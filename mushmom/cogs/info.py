"""
Character profiles

"""
import discord
import asyncio
import re

from discord import app_commands
from discord.ext import commands
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union
from aenum import Enum

from .. import config, mapleio
from .utils import errors, converters
from .utils.parameters import contains
from .reference import ERRORS
from ..mapleio import imutils
from ..mapleio.character import Character

from ..resources import EMOJIS, ATTACHMENTS, BACKGROUNDS
from ..mapleio.resources import JOBS, GAMES, SERVERS

UTC = timezone.utc
NYC = ZoneInfo('America/New_York')  # new york timezone
Games = Enum('Games', GAMES)


def utc(ts):
    return ts.replace(tzinfo=UTC)


class Info(commands.Cog):
    # groups get added in CogMeta. Just used for naming
    set_group = app_commands.Group(name='set', description='Set things')

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    async def info(
            self,
            interaction: discord.Interaction,
            member: Optional[discord.Member] = None
    ) -> None:
        """
        Discord member profile. Reacting with \U0001f44d or \U0001f44e
        will fame/defame this member

        Parameters
        ----------
        interaction: discord.Interaction
        member: Optional[discord.Member]
            member's profile to show. If not supplied, caller's profile

        """
        if not member:
            member = interaction.user

        msg = f'{config.core.bot_name} is thinking'
        await self.bot.defer(interaction, msg=msg, ephemeral=False)

        embed = discord.Embed(
            title=f'{member.name}#{member.discriminator}',
            color=config.core.embed_color
        )
        mushhuh = self.bot.get_emoji_url(EMOJIS['mushhuh'].id)
        embed.set_author(name=f'{member.display_name}\'s Info',
                         icon_url=mushhuh)
        embed.set_thumbnail(url=member.display_avatar.url)

        # get user info
        user = await self.bot.db.get_user(member.id)

        if not user:
            user = char = {}
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
        _fmt_info = [_padded_str(f'> **{k.title()}**: {v}')
                     for k, v in char_info.items()]
        embed.add_field(name='Active Character',
                        value='\n'.join(_fmt_info) + '\n\u200b')
        _fmt_fame = _padded_str(f'\u2b50 {fame}', n=12)
        embed.add_field(name='Fame', value=_fmt_fame + '\n\u200b')

        # send placeholder pfp in 3 seconds
        temp = ATTACHMENTS['pfp_loading']
        pfp_temp = self.bot.get_attachment_url(*temp)
        embed.set_image(url=pfp_temp)
        embed.set_footer(text='Still loading profile picture')
        temp_send_task = self.bot.loop.create_task(
            self._delayed_send(interaction, content='', embed=embed)
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
        args = dict(content='', embed=embed)

        if not temp_send_task.done():
            temp_send_task.cancel()

            if pfp:
                embed.set_image(url=f'attachment://{filename}')
                args['attachments'] = [pfp]
            else:
                pfp_poo = self.bot.get_attachment_url(*ATTACHMENTS['pfp_poo'])
                embed.set_image(url=pfp_poo)
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

        # send the updated message
        msg = await self.bot.followup(interaction, **args)

        # start waiting for fame reactions
        if user:
            self.bot.info_cache.add(msg.id, member.id)

    async def _delayed_send(self, interaction, delay=3, **kwargs):
        await asyncio.sleep(delay)
        return await self.bot.followup(interaction, **kwargs)

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
        if bg in BACKGROUNDS:
            attm, y_ground = BACKGROUNDS[bg]
            url = self.bot.get_attachment_url(*attm)
        else:
            url, y_ground = bg, 0

        bg_data = await self.bot.download(url)
        bg = Image.open(BytesIO(bg_data)).convert('RGBA')

        # gen pfp
        w_bg, h_bg = bg.size
        pfp_data = imutils.apply_background(
            data, bg, y_ground=y_ground, crop=False
        )
        pfp = Image.open(BytesIO(pfp_data)).convert('RGBA')
        pfp = pfp.crop(((w_bg - w)//2, (h_bg - h), (w_bg + w)//2, h_bg))

        byte_arr = BytesIO()
        pfp.save(byte_arr, format='PNG')
        return byte_arr.getvalue()

    @set_group.command(name="info")
    @app_commands.autocomplete(job=contains(JOBS),
                               server=contains(SERVERS))
    async def _set_info(
            self,
            interaction: discord.Interaction,
            job: Optional[str] = None,
            game: Optional[Games] = None,
            server: Optional[str] = None,
            guild: Optional[str] = None
    ):
        """
        Set the information displayed in /info. Enter whitespace to clear

        Parameters
        ----------
        interaction: discord.Interaction
        job: Optional[str]
            E.g. Bishop, Hero, etc.
        game: Optional[Games]
            Maplestory/MaplestoryM
        server: Optional[str]
            E.g. Scania (A1), Luna (EU), Reboot (NA), etc.
        guild: Optional[str]
            your guild

        """
        input = locals().copy()
        input['game'] = input['game'].value if input['game'] else None  # enum
        user = await self.bot.db.get_user(interaction.user.id)

        if not user or not user['chars']:
            raise errors.NoCharacters

        char = user['chars'][user['default']]
        input['name'] = char.get('name')

        # only send modal when no args are passed
        if not (job or game or server or guild):
            modal = SetInfoModal(char)
            await interaction.response.send_modal(modal)
            await modal.wait()

            if not modal.submit:  # cancelled
                return

            interaction = modal.submit
            for field in Character._info_attrs + ['name']:
                input[field] = getattr(modal, field).value
        else:
            await self.bot.defer(interaction)

        # validate input. can be NA
        update, invalid = {}, []
        to_validate = {  # key, list
            'job': JOBS,
            'game': [x.name for x in Games],
            'server': SERVERS
        }

        for k, valid in to_validate.items():
            if input[k] and input[k] != char.get(k):  # whitespace to clear
                if input[k] in valid or input[k].isspace():
                    update[k] = input[k].strip()
                else:
                    invalid.append(k)

        # ensure not just whitespace
        if input['name'] != char.get('name') and input['name'].strip():
            update['name'] = input['name']

        if input['guild'] != char.get('guild'):
            update['guild'] = input['guild'].strip()

        # update database
        if update:
            char.update(update)
            _update = {'chars': user['chars']}
            ret = await self.bot.db.set_user(interaction.user.id, _update)

            if ret and ret.acknowledged:
                text = f'Updated: **{", ".join(update.keys())}**'
                await self.bot.followup(interaction, content=text)
            else:
                raise errors.DatabaseWriteError

        if invalid:
            text = 'The following issues occurred:\n\u200b'
            embed = discord.Embed(description=text, color=config.core.embed_color)
            mushshock = self.bot.get_emoji_url(EMOJIS['mushshock'].id)
            embed.set_thumbnail(url=mushshock)
            embed.set_author(name='Warning',
                             icon_url=self.bot.user.display_avatar.url)

            errs = [f'**{input[k]}** is not a valid format for **{k}**'
                    for k in invalid]
            embed.add_field(name='Warnings', value='\n'.join(errs))
            await self.bot.followup(interaction, embed=embed)

    async def _fame(
            self,
            user: discord.Member,
            member: discord.Member,
            amt: int = 1,
            channel: Optional[discord.abc.Messageable] = None
    ) -> None:
        """
        Internal function for adding fame (or defame). Bot owner
        will circumvent all checks.

        Parameters
        ----------
        user: discord.Member
            the member faming
        member: discord.Member
            the member to fame
        amt: int
            the amount to fame. can be negative
        channel: Optional[discord.abc.Messageable]
            channel to send confirmation message to. can be None

        """
        if user.id == member.id and user.id != self.bot.owner_id:
            raise errors.SelfFameError

        target = await self.bot.db.get_user(member.id)
        if not target:
            raise errors.DataNotFound

        update = {'fame': target['fame'] + amt}

        # owner can fame whenever
        if user.id == self.bot.owner_id:
            await self.bot.db.set_user(member.id, update)
        else:
            # regular user
            famer = await self.bot.db.get_user(user.id)
            if not famer:
                ret = await self.bot.db.add_user(user.id)
                if not ret.acknowledged:
                    raise errors.DataWriteError
                else:
                    famer = await self.bot.db.get_user(user.id)

            # check if already famed or max fame reached
            fame_log = FameLog(famer['fame_log'])

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

                await self.bot.db.set_user(user.id, {'fame_log': fame_log})
            else:
                raise errors.DataWriteError

        if channel:
            verb = f'{"de" if amt < 0 else ""}famed'
            await channel.send(f'You {verb} **{member.display_name}**')

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
        await self._fame(ctx.author, member, 1, ctx.channel)

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
        await self._fame(ctx.author, member, -1, ctx.channel)

    @commands.Cog.listener()
    async def on_reaction_add(
            self,
            reaction: discord.Reaction,
            user: Union[discord.Member, discord.User]
    ) -> None:
        """
        Monitor for fame/defame reactions to info.  Will only monitor
        for 10 minutes and all fame restrictions apply.  Errors will
        @mention the user
        
        Parameters
        ----------
        reaction: discord.Reaction
            the reaction added
        user: Union[discord.Member, discord.User]
            the user that added the reaction

        """
        if reaction.message not in self.info_cache:
            return

        member_id = self.info_cache.get(reaction.message)
        member = (self.bot.get_user(member_id)
                  or await self.bot.fetch_user(member_id))
        name = (reaction.emoji if isinstance(reaction.emoji, str)
                else reaction.emoji.name)

        try:
            cmd = None
            if str(reaction) == '\U0001f44D' or 'thumbsup' in name.lower():
                cmd, amt = 'fame', 1
                await self._fame(user, member, 1)
            elif str(reaction) == '\U0001f44E' or 'thumbsdown' in name.lower():
                cmd, amt = 'defame', -1
                await self._fame(user, member, -1)

            if cmd:
                # edit embed. fame is the 2nd field
                embed = reaction.message.embeds[0]
                curr = re.search(r'\d+', embed.fields[1].value).group()
                _fmt_fame = self._padded_str(f'\u2b50 {int(curr) + amt}', n=12)
                embed.set_field_at(1, name='Fame', value=_fmt_fame + '\n\u200b')

                # attached pfp pops out of embed, so remove
                await reaction.message.edit(embed=embed, attachments=[])
        except errors.MushmomError as error:
            err = f'errors.{error.__class__.__name__}'
            specs = ERRORS[self.__class__.__name__.lower()][cmd][err]
            msg, ref_cmds = specs.values()
            ctx = await self.bot.get_context(reaction.message)
            await self.bot.send_error(ctx, msg, ref_cmds,
                                      delete_message=False,
                                      raw_content=f'{user.mention}')


def _padded_str(text, n=30):
    s = list('\xa0' * n)
    s[:len(text)] = list(text)
    return ''.join(s)


class SetInfoModal(discord.ui.Modal, title='Set Info'):
    def __init__(self, char: dict):
        super().__init__()

        self.char = char
        self.submit = None

        # items
        self.name = discord.ui.TextInput(
            label='Name',
            placeholder="Enter your character's name...",
            max_length=30,
            default=char.get('name'),
        )
        self.job = discord.ui.TextInput(
            label='Job',
            placeholder="E.g. Bishop, Hero, etc.",
            default=char.get('job'),
            required=False
        )
        self.game = discord.ui.TextInput(
            label='Game',
            placeholder="Maplestory/MaplestoryM",
            default=char.get('game'),
            required=False
        )
        self.server = discord.ui.TextInput(
            label='Server',
            placeholder="E.g. Scania (A1), Luna (EU), Reboot (NA), etc.",
            default=char.get('server'),
            required=False
        )
        self.guild = discord.ui.TextInput(
            label='Guild',
            placeholder="Enter your guild...",
            default=char.get('guild'),
            required=False
        )

        # add inputs
        self.add_item(self.name)
        for field in Character._info_attrs:
            self.add_item(getattr(self, field))

    async def on_submit(self, interaction: discord.Interaction):
        self.submit = interaction
        text = f'<a:loading:{EMOJIS["loading"].id}> Processing'
        await interaction.response.send_message(text, ephemeral=True)
        self.stop()


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


async def setup(bot):
    await bot.add_cog(Info(bot))
