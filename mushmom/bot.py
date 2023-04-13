from __future__ import annotations  # forward reference

import discord
import sys
import aiohttp
import asyncio
import warnings
import traceback
import functools
import time
import logging

from discord.ext import commands, tasks
from discord import Emoji, Reaction, PartialEmoji
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from typing import Optional, Union, Iterable

from . import config, database as db, mapleio
from .cogs import reference
from .cogs.utils import errors, checks, io
from .cogs.resources import EMOJIS

_log = logging.getLogger('discord')

initial_extensions = (
    'cogs.meta',
    'cogs.help',
    'cogs.self',
    'cogs.info',
    'cogs.actions',
    'cogs.characters',
    'cogs.import',
    'cogs.emotes',
    'cogs.server',
    'cogs.sprites',
    'cogs.mush',
    'cogs.errors',
    'cogs.list'
)


async def _prefix_callable(
        bot: Mushmom,
        message: discord.Message
) -> Iterable[str]:
    """
    Get guild prefixes if exist else use defaults. Also allow mentions

    Parameters
    ----------
    bot: commands.Bot
    message: discord.Message

    Returns
    -------
    Iterable[str]
        list of prefixes

    """
    _default = config.core.default_prefix
    default = [_default] if isinstance(_default, str) else _default
    guild = await bot.db.get_guild(message.guild.id)
    prefixes = default + (guild['prefixes'] if guild else [])
    return commands.when_mentioned_or(*prefixes)(bot, message)


class Mushmom(commands.Bot):
    """
    Bot used to send emotes and sprites by making API calls to
    maplestory.io

    Parameters
    ----------
    db_client: AsyncIOMotorClient
        an active client connected to MongoDB

    Attributes
    ----------
    session: aiohttp.ClientSession
        client for making async http requests
    reply_cache: ReplyCache
        an expiring cache of replies to processed messages for
        subsequent interaction or clean up
    db: AsyncIOMotorDatabase
        the MongoDB database holding collections

    """
    def __init__(
            self,
            db_client: AsyncIOMotorClient,
            sync: Optional[int, bool] = None  # specific guild id or all
    ):
        intents = discord.Intents.default()

        super().__init__(command_prefix=_prefix_callable, intents=intents)
        self.session = None  # set in on_ready
        self.user_agent = '{bot}/{version} {default}'.format(
            bot=config.core.bot_name,
            version=config.core.version,
            default=aiohttp.http.SERVER_SOFTWARE
        )

        self.reply_cache = io.MessageCache(seconds=300)
        self.db = db.Database(db_client)
        self.timer = Timer()
        self.init_sync = sync

        # add global checks
        self.add_check(checks.not_bot)
        self.add_check(checks.in_guild_channel)

    async def setup_hook(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                loop=self.loop,
                headers={
                    'User-Agent': self.user_agent
                }
            )

        # set owner. assume not team
        if not self.owner_id:
            app = await self.application_info()
            self.owner_id = app.owner.id

        # load extensions
        self.remove_command('help')
        for ext in initial_extensions:
            await self.load_extension(f'{__package__}.{ext}')

        # sync slash commands
        if self.init_sync:
            guild = (discord.Object(id=self.init_sync)  # bool subclass int
                     if type(self.init_sync) is int else None)

            cmds = await self.tree.sync(guild=guild)
            _log.info(f'{len(cmds)} slash command(s) synced')

    async def on_ready(self):
        _log.info(f'{self.user} is ready to mush!')

        if not self._verify_cache_integrity.is_running:
            self._verify_cache_integrity.start()

    async def on_message(self, message: discord.Message) -> None:
        """
        Call emotes if no command found and emote name is passed

        Parameters
        ----------
        message: discord.Message

        """
        ctx = await self.get_context(message)
        cmd = ctx.command
        self.timer.start(ctx)

        # not handled by other commands
        if (ctx.prefix and not cmd
                and all([await c(ctx) for c in self._checks])):
            no_prefix = message.content[len(ctx.prefix):]
            args = no_prefix.split(' ')
            cmd = args.pop(0)

            # manually try to call as emote command
            if cmd not in mapleio.resources.EMOTIONS:
                return

            message.content = f'{ctx.prefix}emote {no_prefix}'
            new_ctx = await self.get_context(message)
            cmd = new_ctx.command
            await self.invoke(new_ctx)
        else:
            await self.process_commands(message)

        # track command calls
        if config.database.track and cmd and not cmd.hidden:
            await self.db.track(
                ctx.guild.id, ctx.author.id, cmd.qualified_name)

        self.timer.stop(ctx)

    async def on_command_error(
            self,
            ctx: commands.Context,
            error: Exception
    ) -> None:
        """
        Override default error handler to always run. Errors messages
        are pulled from cogs.reference.ERRORS.

        Local error handlers can still be used. If a reply already
        exists in self.reply_cache, on_command_error will assume it has
        handled notifying user of the issue and pass

        Parameters
        ----------
        ctx: commands.Context
        error: Exception

        """
        if ctx.message in self.reply_cache:  # already sent message
            self.reply_cache.remove(ctx.message)
            return

        if isinstance(error, commands.CommandNotFound):
            return  # ignore

        cmd = ctx.command.qualified_name
        cog = ctx.command.cog_name.lower()
        err_ns = ('errors' if isinstance(error, errors.MushmomError)
                  else 'commands')
        err = f'{err_ns}.{error.__class__.__name__}'

        try:  # search for error
            specs = reference.ERRORS[cog][cmd][err]
            msg, ref_cmds = specs.values()
        except KeyError:  # not defined
            e = error
            if not isinstance(e, commands.CheckFailure) or config.core.debug:
                print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            return

        await self.send_error(ctx, msg, ref_cmds)

    async def send_error(
            self,
            ctx: commands.Context,
            text: Optional[str] = None,
            ref_cmds: Optional[Iterable[str]] = None,
            delete_message: bool = not config.core.debug,
            delete_error: bool = not config.core.debug,
            delay: int = config.core.default_delay,
            raw_content: Optional[str] = None
    ) -> discord.Message:
        """
        Send a message to ctx.channel with an error message. The
        original message and the error message will auto-delete after
        a few seconds to keep channel clean

        Parameters
        ----------
        ctx: commands.Context
        text: Optional[str]
            the message to send in embed
        ref_cmds: Optional[Iterable[str]]
            list of fully qualified command names to reference
        delete_message: bool
            whether or not to auto delete message
        delete_error: bool
            whether or not to auto delete error
        delay: int
            seconds to wait before deleting
        raw_content: Optional[str]
            content to pass directly to send, outside embed

        Returns
        -------
        discord.Message
            the error message that was sent

        """
        # defaults
        if text is None:
            text = 'Mushmom failed *cry*'

        if ref_cmds is None:
            ref_cmds = []

        # send error
        embed = discord.Embed(description=text,
                              color=config.core.embed_color)
        embed.set_author(name='Error', icon_url=ctx.bot.user.display_avatar.url)
        embed.set_thumbnail(url=ctx.bot.get_emoji_url(EMOJIS['mushshock']))

        # add referenced commands
        help_cog = self.get_cog('Help')

        if help_cog:
            usages = help_cog.get_all_usages(ctx, ref_cmds, aliases=True)

            if usages:
                embed.add_field(name='Commands', value='\n'.join(usages))

        error = await ctx.send(content=raw_content, embed=embed,
                               delete_after=delay if delete_error else None)

        # delete original message after successful send
        if delete_message:
            try:
                await ctx.message.delete(delay=delay)
            except commands.MissingPermissions:
                pass

        return error

    @staticmethod
    async def ephemeral(
            interaction: discord.Interaction,
            *args,
            **kwargs
    ) -> None:
        """
        Helper function for ephemeral interactions using default timers

        """
        await interaction.response.send_message(*args, **kwargs, ephemeral=True)

    @staticmethod
    async def defer(interaction: discord.Interaction) -> None:
        """
        Convenience function for ephemeral thinking

        """
        await interaction.response.defer(ephemeral=True, thinking=True)

    @staticmethod
    async def followup(
            interaction: discord.Interaction,
            *,  # only key word arguments, since edit only takes kwargs
            delete_after: Optional[int] = None,
            **kwargs
    ) -> None:
        """
        Version of followup that keeps overwriting the orig message

        Parameters
        ----------
        interaction: discord.Interaction
        delete_after: Optional[int]
            ms to wait before deleting

        """
        await interaction.edit_original_response(**kwargs)

        if delete_after is not None:
            await asyncio.sleep(delete_after)
            await interaction.delete_original_response()

    @staticmethod
    async def send_as_author(
            interaction: discord.Interaction,
            *args,
            **kwargs
    ) -> discord.Message:
        """
        Use webhook to send a message with author's name and pfp.
        Create one if does not exist

        Parameters
        ----------
        interaction: discord.Interaction
        args
            passed to discord.Webhook.send
        kwargs
            passed to discord.Webhook.send

        Returns
        -------
        discord.Message
            the message that was sent

        """
        webhooks = await interaction.channel.webhooks()
        hook_name = config.core.hook_name
        webhook = next((wh for wh in webhooks if wh.name == hook_name), None)

        # create if does not exist
        if not webhook:
            webhook = await interaction.channel.create_webhook(name=hook_name)

        user = interaction.user
        return await webhook.send(*args, **kwargs,
                                  wait=True,
                                  username=user.display_name,
                                  avatar_url=user.display_avatar.url)

    @staticmethod
    async def add_delayed_reaction(
            ctx: commands.Context,
            reaction: Union[Emoji, Reaction, PartialEmoji, str],
            delay: int = config.core.delayed_react_time
    ) -> None:
        """
        Add a reaction after some time

        Parameters
        ----------
        ctx: commands.Context
        reaction: Union[Emoji, Reaction, PartialEmoji, str]
            the reaction/emoji to add
        delay: int
            seconds to wait before adding reaction

        """
        await asyncio.sleep(delay)
        await ctx.message.add_reaction(reaction)

    async def wait_for_reaction(
            self,
            ctx: commands.Context,
            prompt: discord.Message,
            reactions: dict[str, Union[discord.Emoji, discord.PartialEmoji, str]]
    ) -> str:
        """
        Add reactions to message and wait for original author response

        Parameters
        ----------
        ctx: commands.Context
        prompt: discord.Message
            the message to which to add reactions
        reactions: dict[str, Union[discord.Emoji, discord.PartialEmoji, str]]
            key is meaning of reaction, value is the reaction

        Returns
        -------
        str
            the key value associated with selected reaction

        """
        # add reactions
        for reaction in reactions.values():
            await prompt.add_reaction(reaction)

        # wait for reaction
        try:
            reaction, user = (
                await ctx.bot.wait_for(
                    'reaction_add',
                    check=lambda r, u: (u == ctx.author
                                        and r.message.id == prompt.id
                                        and r.emoji in reactions.values()),
                    timeout=config.core.default_delay
                )
            )
        except asyncio.TimeoutError:
            # delete immediately so main error handler runs
            if not config.core.debug:
                try:
                    await prompt.delete()
                except commands.MissingPermissions:
                    pass

            self.reply_cache.remove(ctx.message)
            raise errors.TimeoutError  # handle in command errors

        return next(k for k, v in reactions.items() if reaction.emoji == v)

    @property
    def ref_aliases(self) -> dict[str, commands.Command]:
        """
        Checks reference.HELP for commands with aliases listed

        Returns
        -------
        dict[str, commands.Command]
            key is alias, value is command

        """
        return {alias: self.get_command(cmd, default=True)
                for cog, cmds in reference.HELP.items()
                for cmd, info in cmds.items() if 'aliases' in info
                for alias in info['aliases']}

    def get_command(
            self,
            name: str,
            default: bool = False
    ) -> Optional[commands.Command]:
        """
        Overwrite default behavior of allowing extraneous tokens
        after command. Also checks reference.HELP for looser alias naming
        (e.g. can have spaces)

        Parameters
        ----------
        name: str
            the name of command to get
        default: bool
            whether or not to use the default implementation

        Returns
        -------
        commands.Command
            the found command or None

        Notes
        -----
        Default implementation would allow the following

        >>> bot.get_command('hello asdf')
        Command(name=hello, ...)

        """
        if default:
            return super().get_command(name)

        # fast path, no space in name.
        if ' ' not in name:
            return self.all_commands.get(name)

        if name in self.ref_aliases:  # check reference.HELP
            return self.ref_aliases[name]

        # handle groups
        names = name.split()
        if not names:
            return None
        obj = self.all_commands.get(names[0])
        if not isinstance(obj, commands.GroupMixin):
            return obj if len(names) == 1 else None

        for i, name in enumerate(names[1:]):
            try:
                obj = obj.all_commands[name]
            except (AttributeError, KeyError):
                return None

        return obj if i == len(names)-2 else None

    def get_emoji_url(self, emoji_id: int) -> str:
        """
        Convenience wrapper to pull url from emoji

        Parameters
        ----------
        emoji_id: int
            the discord emoji id

        Returns
        -------
        str
            the emoji url or bot avatar url

        """
        emoji = self.get_emoji(emoji_id)

        if emoji:
            return emoji.url
        else:
            warnings.warn(f'Emoji<{emoji_id}> was not found', ResourceWarning)
            return self.user.display_avatar.url  # fall back on profile pic

    @staticmethod
    def get_attachment_url(
            channel_id: int,
            attachment_id: int,
            filename: str
    ) -> str:
        """
        Combine to get an attachment url

        Parameters
        ----------
        channel_id: int
            the channel id
        attachment_id:
            the attachment id
        filename: str
            the filename

        Returns
        -------
        str
            the attachment url

        """
        path = 'https://cdn.discordapp.com/attachments'
        return f'{path}/{channel_id}/{attachment_id}/{filename}'

    async def download(
            self,
            url: str,
            error: type[Exception] = web.HTTPError
    ) -> bytes:
        """
        Download a url

        Parameters
        ----------
        url: str
            the url to download
        error: type[Exception]
            error to raise if fails

        Returns
        -------
        bytes
            the response content

        """
        async with self.session.get(url) as r:
            if r.status != 200:
                raise error

            return await r.read()

    @tasks.loop(minutes=10)
    async def _verify_cache_integrity(self):
        """Clean up stray cached replies"""
        self.reply_cache.verify_cache_integrity()

    async def close(self):
        """Ensure all connections are closed"""
        await super().close()
        await self.session.close()
        self.db.close()


class Timer:
    """
    Add to on_message and prints time to process message if active
    and a command was called.  Not fully implemented

    Attributes
    ----------
    active: bool
        whether or not a the timer should time
    timing: bool
        whether or not timing is happening
    conditions: dict[str, str]
        conditions to check by getting values from a commands.Context

    """
    def __init__(self):
        self.active = False
        self.timing = False
        self.conditions = {}

        # private
        self._start = None
        self._ctx = None

    def activate(self, conditions: Optional[dict] = None):
        """Allows start and stop to print based on conditions"""
        self.active = True
        self.conditions = conditions

    def deactivate(self):
        self.active = False
        self.conditions = {}

    def start(self, ctx: commands.Context):
        if ctx.command:
            self.timing = True
            self._start = time.monotonic()
            self._ctx = ctx

    def stop(self, ctx: commands.Context):
        if (self.active and self.timing
                and ctx.message.id == self._ctx.message.id):
            delta = time.monotonic() - self._start
            print('{}: {:.2f}s'.format(ctx.command.qualified_name, delta))
            self.timing = False
            self._start = None

    @staticmethod
    def rgetattr(obj, attr, *args):
        def _getattr(obj, attr):
            return getattr(obj, attr, *args)
        return functools.reduce(_getattr, [obj] + attr.split('.'))
