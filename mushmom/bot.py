from __future__ import annotations  # forward reference

import discord
import aiohttp
import asyncio
import warnings
import functools
import time
import logging

from discord.ext import commands, tasks
from discord import Emoji, Reaction, PartialEmoji
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from typing import Optional, Union, Iterable

from . import config, database as db
from .cache import TTLCache
from .cogs.utils import errors, checks, io
from .resources import EMOJIS

_log = logging.getLogger('discord')

initial_extensions = (
    'cogs.meta',
    'cogs.self',
    'cogs.info',
    'cogs.actions',
    'cogs.characters',
    'cogs.server',
    'cogs.mush',
    'cogs.error_handler',
    'cogs.list',
    'cogs.pose'
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
    info_cache: TTLCache
        an expiring cache of info msg that can be reacted to for fame
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

        self.info_cache = TTLCache(seconds=300)
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
    async def defer(
            interaction: discord.Interaction,
            msg: Optional[str] = None,
            ephemeral: bool = True
    ) -> None:
        """
        Convenience function for ephemeral thinking

        Parameters
        ----------
        interaction: discord.Interaction
        msg: Optional[str]
            message to send after ellipses
        ephemeral: bool
            whether or not to only show to user

        """
        if msg is not None:
            _msg = f'<a:loading:{EMOJIS["loading"].id}> {msg}'
            await interaction.response.send_message(_msg, ephemeral=ephemeral)
        else:
            await interaction.response.defer(ephemeral=ephemeral, thinking=True)

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
        msg = await interaction.edit_original_response(**kwargs)

        if delete_after is not None:
            await asyncio.sleep(delete_after)
            await interaction.delete_original_response()

        return msg

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
        """Clean up stray cached data"""
        self.info_cache.verify_cache_integrity()
        self.db.user_cache.verify_cache_integrity()

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
