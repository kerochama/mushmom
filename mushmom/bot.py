from __future__ import annotations  # forward reference

import discord
import sys
import aiohttp
import asyncio
import warnings
import traceback
import time

from discord.ext import commands, tasks
from discord import Emoji, Reaction, PartialEmoji
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Union, Iterable

from . import config
from .utils import checks, errors, database as db, converters
from .mapleio import resources
from .cogs import ref

initial_extensions = (
    'cogs.core',
    'cogs.meta',
    'cogs.help',
    'cogs.characters',
    'cogs.import',
    'cogs.emotes',
    'cogs.sprites'
)


async def _prefix_callable(
        bot: Mushmom,
        message: discord.Message
) -> Iterable[str]:
    """
    Get guild prefixes if exist else use defaults

    Parameters
    ----------
    bot: commands.Bot
    message: discord.Message

    Returns
    -------
    Iterable[str]
        list of prefixes

    """
    default = [config.core.default_prefix]
    guild = await bot.db.get_guild(message.guild.id)

    if not guild:
        return default
    else:
        return guild['prefixes'] + default


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
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(command_prefix=_prefix_callable)
        self.session = None  # set in on_ready
        self.reply_cache = ReplyCache(seconds=300)
        self.db = db.Database(db_client)

        # add global checks
        self.add_check(checks.not_bot)
        self.add_check(checks.in_guild_channel)

        # load extensions
        self.remove_command('help')
        for ext in initial_extensions:
            self.load_extension(f'{__package__}.{ext}')

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')
        self.session = aiohttp.ClientSession(loop=self.loop)

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

        # not handled by other commands
        if (ctx.prefix and not ctx.command
                and all([await check(ctx) for check in self._checks])):
            no_prefix = message.content[len(ctx.prefix):]
            args = no_prefix.split(' ')
            cmd = args.pop(0)

            # manually try to call as emote command
            if cmd not in resources.EMOTIONS:
                return

            message.content = f'{ctx.prefix}emote {no_prefix}'
            new_ctx = await self.get_context(message)
            await self.invoke(new_ctx)
        else:
            await self.process_commands(message)

    async def on_command_error(
            self,
            ctx: commands.Context,
            error: Exception
    ) -> None:
        """
        Override default error handler to always run. Errors messages
        are pulled from cogs.ref.ERRORS.

        Local error handlers can still be used. If a reply already
        exists in self.reply_cache, on_command_error will assume it has
        handled notifying user of the issue and pass

        Parameters
        ----------
        ctx: commands.Context
        error: Exception

        """
        if ctx in self.reply_cache:  # already sent message
            self.reply_cache.remove(ctx)
            return

        cmd = ctx.command.qualified_name
        cog = ctx.command.cog_name.lower()
        err_ns = ('errors' if isinstance(error, errors.MushmomError)
                  else 'commands')
        err = f'{err_ns}.{error.__class__.__name__}'

        try:  # search for error
            specs = ref.ERRORS[cog][cmd][err]
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
            delay: int = config.core.default_delay
    ) -> discord.Message:
        """
        Send a message to ctx.channel with an error message. The
        original message and the error message will auto-delete after
        a few seconds to keep channel clean

        Parameters
        ----------
        ctx: commands.Context
        text: Optional[str]
            the message to send
        ref_cmds: Optional[Iterable[str]]
            list of fully qualified command names to reference
        delete_message: bool
            whether or not to auto delete message
        delay: int
            seconds to wait before deleting

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
        embed.set_author(name='Error', icon_url=ctx.bot.user.avatar.url)
        embed.set_thumbnail(url=ctx.bot.get_emoji_url(config.emojis.mushshock))

        # add referenced commands
        help_cog = self.get_cog('Help')

        if help_cog:
            usages = help_cog.get_usages(ctx, ref_cmds, aliases=True)

            if usages:
                embed.add_field(name='Commands', value='\n'.join(usages))

        error = await ctx.send(embed=embed, delete_after=delay if delete_message else None)

        # delete original message after successful send
        if delete_message:
            await ctx.message.delete(delay=delay)

        return error

    @staticmethod
    async def send_as_author(
            ctx: commands.Context,
            *args,
            **kwargs
    ) -> discord.Message:
        """
        Use webhook to send a message with author's name and pfp.
        Create one if does not exist

        Parameters
        ----------
        ctx: commands.Context
        args
            passed to discord.Webhook.send
        kwargs
            passed to discord.Webhook.send

        Returns
        -------
        discord.Message
            the message that was sent

        """
        webhooks = await ctx.channel.webhooks()
        webhook = next((wh for wh in webhooks if wh.name == config.core.hook_name),
                       None)

        # create if does not exist
        if not webhook:
            webhook = await ctx.channel.create_webhook(name=config.core.hook_name)

        return await webhook.send(*args, **kwargs,
                                  username=ctx.author.display_name,
                                  avatar_url=ctx.author.avatar.url)

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

    def get_command(
            self,
            name: str,
            default: bool = False
    ) -> Optional[commands.Command]:
        """
        Overwrite default to check cogs.ref.HELP for the command name
        first.  Also overwrite default behavior of allowing extraneous
        tokens after command.

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

        # check cogs.ref.HELP
        ref_cmds = {cmd: cog for cog in ref.HELP.keys()
                    for cmd in ref.HELP[cog].keys()}

        try:  # look for command in ref.HELP
            cog = ref_cmds[name]
            _name = ref.HELP[cog][name]['command']
        except KeyError:
            _name = name

        if default:
            return super().get_command()
        # fast path, no space in name.
        if ' ' not in _name:
            return self.all_commands.get(_name)

        names = _name.split()
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
            return self.user.avatar.url  # fall back on profile pic

    @tasks.loop(minutes=10)
    async def _verify_cache_integrity(self):
        """Clean up stray cached replies"""
        self.reply_cache.verify_cache_integrity()

    async def close(self):
        """Ensure all connections are closed"""
        await super().close()
        await self.session.close()
        self.db.close()


class ReplyCache:
    """
    Maintains a cache of messages sent by bot in response to a
    command so that they can be referenced/cleaned subsequently.
    Entries will expire after some time

    Parameters
    ----------
    seconds: int
        the number of seconds to wait before expiring

    """
    def __init__(self, seconds: int):
        self.__ttl = seconds
        self.__cache = {}
        super().__init__()

    def verify_cache_integrity(self) -> None:
        """Loop through cache and remove all expired keys"""
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__cache.items()
                     if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self.__cache[k]

    def get(self, ctx: commands.Context) -> Optional[discord.Message]:
        reply, t = self.__cache.get(ctx.message.id, (None, None))
        current_time = time.monotonic()
        if reply and (t + self.__ttl) <= current_time:
            return reply

    def add(self, ctx: commands.Context, reply: discord.Message) -> None:
        self.__cache[ctx.message.id] = (reply, time.monotonic())

    def remove(self, ctx: commands.Context) -> None:
        self.__cache.pop(ctx.message.id, None)

    def contains(self, ctx: commands.Context) -> bool:
        reply, t = self.__cache.get(ctx.message.id, (None, None))
        current_time = time.monotonic()
        return reply and (t + self.__ttl) <= current_time

    def __contains__(self, ctx: commands.Context) -> bool:
        return self.contains(ctx)

    async def clean_up(
            self,
            ctx: commands.Context,
            delete: bool = not config.core.debug
    ) -> None:
        """Delete key if exists. Also delete reply from discord"""
        reply = self.__cache.pop(ctx, None)

        if reply and delete:
            try:
                await reply.delete()
            except discord.HTTPException:
                pass
