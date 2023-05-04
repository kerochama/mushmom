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
from typing import Optional
from aenum import Enum
from collections import namedtuple

from .. import config, mapleio
from .utils import errors, io
from .utils.parameters import contains
from .utils.checks import slash_in_guild_channel
from ..mapleio import imutils
from ..mapleio.character import Character

from ..resources import EMOJIS, ATTACHMENTS, BACKGROUNDS

UTC = timezone.utc
NYC = ZoneInfo('America/New_York')  # new york timezone
InfoData = namedtuple('InfoData', 'message target')
Games = Enum('Games', mapleio.GAMES)


def utc(ts):
    return ts.replace(tzinfo=UTC)


class Info(commands.Cog):
    # groups get added in CogMeta. Just used for naming
    set_group = app_commands.Group(name='set', description='Set things')

    def __init__(self, bot):
        self.bot = bot
        self._info_context_menu = app_commands.ContextMenu(
            name='Get Info',
            callback=self.info_context_menu
        )
        self.bot.tree.add_command(self._info_context_menu)

    @app_commands.command()
    @slash_in_guild_channel()
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
        mushhuh = self.bot.get_emoji(EMOJIS['mushhuh'].id).url
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
        embed.set_image(url=ATTACHMENTS['pfp_loading'].url)
        embed.set_footer(text='Still loading profile picture')
        temp_send_task = self.bot.loop.create_task(
            self._delayed_send(interaction, content='', embed=embed)
        )

        # get real pfp
        if not char:
            attm = ATTACHMENTS['mushcharnotfound']
            filename = attm.filename

            try:
                data = await self.bot.download(attm.url, errors.DiscordIOError)
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
                embed.set_image(url=ATTACHMENTS['pfp_poo'].url)
        else:
            msg = temp_send_task.result()

            # default fail
            embed.set_image(url=ATTACHMENTS['pfp_poo'].url)

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
            _info = InfoData(msg, member)
            self.bot.info_cache.add(msg.id, _info)

    @slash_in_guild_channel()
    async def info_context_menu(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ) -> None:
        """
        Context menu version of info

        Parameters
        ----------
        interaction: discord.Interaction
        member: Optional[discord.Member]
            member's profile to show

        """
        await self.info.callback(self, interaction, member)

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
            url = attm.url
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
    @app_commands.autocomplete(job=contains(mapleio.JOBS),
                               server=contains(mapleio.SERVERS))
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
            'job': mapleio.JOBS,
            'game': [x.name for x in Games],
            'server': mapleio.SERVERS,
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
            mushshock = self.bot.get_emoji(EMOJIS['mushshock'].id).url
            embed.set_thumbnail(url=mushshock)
            embed.set_author(name='Warning',
                             icon_url=self.bot.user.display_avatar.url)

            errs = [f'**{input[k]}** is not a valid format for **{k}**'
                    for k in invalid]
            embed.add_field(name='Warnings', value='\n'.join(errs))
            await self.bot.followup(interaction, embed=embed)

    @set_group.command(name='pose')
    @app_commands.autocomplete(pose=contains(mapleio.POSES),
                               expression=contains(mapleio.EXPRESSIONS))
    async def _set_pose(
            self,
            interaction: discord.Interaction,
            pose: Optional[str] = None,
            expression: Optional[str] = None
    ) -> None:
        """
        Set default pose for /info

        Parameters
        ----------
        interaction: discord.Interaction,
        pose: Optional[str]
            default pose (shown in info)
        expression: Optional[str]
            default expression (shown in info)

        """
        await self.bot.defer(interaction)

        if pose and pose not in mapleio.POSES.values():
            msg = f'**{pose}** is not a valid pose'
            raise errors.BadArgument(msg, see_also=['list poses'])

        if expression and expression not in mapleio.EXPRESSIONS:
            msg = f'**{expression}** is not a valid expression'
            raise errors.BadArgument(msg, see_also=['list expressions'])

        user = await self.bot.db.get_user(interaction.user.id)

        if not user or not user['chars']:
            raise errors.NoCharacters

        # update
        char = user['chars'][user['default']]
        char['action'] = pose or char['action']
        char['emotion'] = expression or char['emotion']

        update = {'chars': user['chars']}
        ret = await self.bot.db.set_user(interaction.user.id, update)

        if ret and ret.acknowledged:
            text = f"Updated **{char['name']}**'s pose/expression"
            await self.bot.followup(interaction, content=text)
        else:
            raise errors.DatabaseWriteError

    async def _fame(
            self,
            user: discord.Member,
            target: discord.Member,
            amt: int = 1,
    ) -> None:
        """
        Internal function for adding fame (or defame). Bot owner
        will circumvent all checks.

        Parameters
        ----------
        user: discord.Member
            the member faming
        target: discord.Member
            the member to fame
        amt: int
            the amount to fame. can be negative

        """
        if user.id == target.id and user.id != self.bot.owner_id:
            raise errors.SelfFameError

        _target = await self.bot.db.get_user(target.id)
        if not _target:
            msg = f'{target.display_name} has not used {config.core.bot_name}'
            raise errors.NoCharacters(msg)

        target_update = {'fame': _target['fame'] + amt}

        # owner can fame whenever
        if user.id == self.bot.owner_id:
            await self.bot.db.set_user(target.id, target_update)
        else:
            # regular user
            famer = await self.bot.db.get_user(user.id)
            if not famer:
                ret = await self.bot.db.add_user(user.id)
                if not ret.acknowledged:
                    raise errors.DatabaseWriteError
                else:  # cached
                    famer = await self.bot.db.get_user(user.id)

            # check if already famed or max fame reached
            famer_log = FameLog(**famer['fame_log'])
            famed_log = FameLog(**_target['fame_log'])

            if target.id in famer_log:
                raise errors.AlreadyFamedError

            # negative amount is a defame. cnt is separate for each
            cnt = len(famer_log.fames() if amt > 1 else famer_log.defames())

            if cnt >= config.core.fame_daily_limit:
                raise errors.MaxFamesReached

            # add fame
            if amt > 0:
                famer_log.add_fame(target.id)
                famed_log.add_famer(user.id)
            elif amt < 0:
                famer_log.add_defame(target.id)
                famed_log.add_defamer(user.id)

            target_update['fame_log'] = famed_log.to_json()
            reqs = {
                target.id: target_update,
                user.id: {'fame_log': famer_log.to_json()}
            }

            ret = await self.bot.db.bulk_user_update(reqs)

            if not ret.acknowledged:
                raise errors.DatabaseWriteError

    @app_commands.command()
    async def fame(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ) -> None:
        """
        Fame someone (by account). You can only fame up to 10 people a
        day, which will reset at midnight eastern time.

        Parameters
        ----------
        interaction: discord.Interaction
        member: discord.Member
            the member to fame

        """
        await self.bot.defer(interaction)
        await self._fame(interaction.user, member, 1)

        # no error
        msg = f'You famed **{member.display_name}**'
        await self.bot.followup(interaction, content=msg)

    @app_commands.command()
    async def defame(
            self,
            interaction: discord.Interaction,
            member: discord.Member
    ) -> None:
        """
        Defame someone (by account). You can only defame up to 10
        people a day, which will reset at midnight eastern time.

        Parameters
        ----------
        interaction: discord.Interaction
        member: discord.Member
            the member to defame

        """
        await self.bot.defer(interaction)
        await self._fame(interaction.user, member, -1)

        # no error
        msg = f'You defamed **{member.display_name}**'
        await self.bot.followup(interaction, content=msg)

    @commands.Cog.listener()
    async def on_raw_reaction_add(
            self,
            payload: discord.RawReactionActionEvent,
    ) -> None:
        """
        Monitor for fame/defame reactions to info.  Will only monitor
        for 10 minutes and all fame restrictions apply.  Errors will be
        ignored to avoid clutter
        
        Parameters
        ----------
        payload: discord.RawReactionActionEvent

        """
        if payload.message_id not in self.bot.info_cache:
            return

        message, target = self.bot.info_cache.get(payload.message_id)
        react = payload.emoji.name.lower()

        try:
            cmd = None
            if react == '\U0001f44E' or _contains_all(react, ['thumb', 'down']):
                cmd, amt = 'fame', -1
            elif react == '\U0001f44D' or _contains_all(react, ['thumb', 'up']):
                cmd, amt = 'defame', 1

            if cmd:
                await self._fame(payload.member, target, amt)

                # edit embed. fame is the 2nd field
                embed = message.embeds[0]
                curr = re.search(r'\d+', embed.fields[1].value).group()
                _fmt_fame = _padded_str(f'\u2b50 {int(curr) + amt}', n=12)
                embed.set_field_at(1, name='Fame', value=_fmt_fame + '\n\u200b')

                # attached pfp pops out of embed, so remove
                await message.edit(embed=embed, attachments=[])
        except errors.MushError:
            pass  # ideally either DM or ephemeral (but no interaction)

        self.bot.info_cache.refresh(payload.message_id)  # extend


def _padded_str(text, n=30):
    s = list('\xa0' * n)
    s[:len(text)] = list(text)
    return ''.join(s)


def _contains_all(string, iterable):
    return all(s in string for s in iterable)


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


FameRecord = namedtuple('FameRecord', 'uid amt ts')


class FameLog:
    """
    Log of fames made and famers (mostly for viewing).  Keep track of
    userid, amount, and timestamp. timestamp is output of datetime.utcnow()
    (i.e. tz unaware, but utc)

    Records that are not from today are removed on init.  Slight inconsistency
    if time between init and operation crosses midnight

    """
    def __init__(self, fames: list, famers: Optional[list] = None):
        utcnow = utc(datetime.utcnow())
        today = utcnow.astimezone(NYC).date()
        famers = famers or []

        # clean old records. iterate over copy
        self._fames = [FameRecord(*fame) for fame in fames
                       if utc(fame[-1]).astimezone(NYC).date() == today]

        self._famers, self._defamers = [], []
        famers.sort(key=lambda x: x[1], reverse=True)

        for fame in famers:
            _fame = FameRecord(*fame)
            lst = self._famers if _fame.amt > 0 else self._defamers

            if len(self._famers) <= config.core.fame_log_length:
                lst.append(_fame)

    def fames(self):
        return [fame for fame in self._fames if fame.amt > 0]

    def defames(self):
        return [fame for fame in self._fames if fame.amt < 0]

    def __contains__(self, uid):
        for fame in self._fames:
            if fame.uid == uid:
                return True

        return False

    def add_fame(self, uid):
        self._fames.append(FameRecord(uid, 1, datetime.utcnow()))

    def add_defame(self, uid):
        self._fames.append(FameRecord(uid, -1, datetime.utcnow()))

    def add_famer(self, uid):
        if len(self._famers) == config.core.fame_log_length:
            self._famers.pop()

        self._famers.append(FameRecord(uid, 1, datetime.utcnow()))

    def add_defamer(self, uid):
        if len(self._defamers) == config.core.fame_log_length:
            self._defamers.pop()

        self._defamers.append(FameRecord(uid, -1, datetime.utcnow()))

    def to_json(self):
        return {
            'fames': self._fames,
            'famers': self._famers + self._defamers
        }


async def setup(bot):
    await bot.add_cog(Info(bot))
