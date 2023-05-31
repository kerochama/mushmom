from __future__ import annotations  # forward reference

import discord
import aiohttp
import asyncio
import logging

from discord.ext import commands, tasks
from discord import Emoji, Reaction, PartialEmoji, app_commands
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from datetime import datetime
from typing import Optional, Union
from collections import namedtuple

from . import config, database as db
from .cache import TTLCache, CachedCommandTree
from .cogs.help import FullHelpCommand
from .cogs.utils import errors, checks
from .resources import EMOJIS

_log = logging.getLogger('discord')

initial_extensions = (
    'cogs.meta',
    'cogs.error_handler',
    'cogs.help',
    'cogs.server',
    'cogs.actions',
    'cogs.characters',
    'cogs.info',
    'cogs.list',
    'cogs.mush',
    'cogs.pose'
)

TrackRecord = namedtuple('TrackRecord', 'guildid userid command ts extras')


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
            sync: Optional[int, bool] = None,  # specific guild id or all
            enable_tracking: bool = True
    ):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=FullHelpCommand(),
            tree_cls=CachedCommandTree
        )

        self.session = None  # set in on_ready
        self.user_agent = '{bot}/{version} {default}'.format(
            bot=config.core.bot_name,
            version=config.core.version,
            default=aiohttp.http.SERVER_SOFTWARE
        )

        self.info_cache = TTLCache(seconds=600)
        self.db = db.Database(db_client)
        self.init_sync = sync

        # add global checks
        self.add_check(checks.not_bot)
        self.add_check(checks.in_guild_channel)

        # store tracking to push at once
        self.enable_tracking = enable_tracking
        self._tracking = []

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

        # update help command cog
        self.help_command.cog = self.get_cog(config.core.bot_name)

        # sync slash commands
        if self.init_sync:
            guild = self.init_sync if type(self.init_sync) is int else None
            _log.info(
                await self.get_cog('Meta')._sync(guild)
            )

        # update guild cache
        await self.db.initialize_guild_cache()

        # start tasks
        self.prune_caches.start()
        self.push_tracking.start()

    async def on_ready(self):
        _log.info(f'{self.user} is ready to mush!')

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
    ) -> discord.InteractionMessage:
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
            try:
                await prompt.delete()
            except commands.MissingPermissions:
                pass

            self.reply_cache.remove(ctx.message)
            raise errors.TimeoutError  # handle in command errors

        return next(k for k, v in reactions.items() if reaction.emoji == v)

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

    async def on_app_command_completion(
            self,
            interaction: discord.Interaction,
            command: app_commands.Command
    ) -> None:
        """Track if tracking is enabled"""
        if self.enable_tracking:
            record = TrackRecord(
                guildid=interaction.guild_id,
                userid=interaction.user.id,
                command=command.qualified_name,
                ts=datetime.utcnow(),
                extras=interaction.extras
            )
            self._tracking.append(record)

    @tasks.loop(minutes=5)
    async def push_tracking(self):
        """Push internally stored tracking to database"""
        if self._tracking:
            await self.db.update_tracking(self._tracking)

        self._tracking = []  # clear

    @tasks.loop(minutes=10)
    async def prune_caches(self):
        """Clean up stray cached data"""
        self.info_cache.prune()
        self.db.user_cache.prune()

    async def close(self):
        """Ensure all connections are closed"""
        await self.push_tracking()
        await super().close()
        await self.session.close()
        self.db.close()
