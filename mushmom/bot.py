import discord
import sys
import aiohttp
import warnings
import traceback

from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient

from . import config
from .utils import checks, io, errors, database as db
from .mapleio import resources
from .cogs import ref


initial_extensions = (
    'cogs.core',
    'cogs.meta',
    'cogs.help',
    'cogs.characters',
    'cogs.import',
    'cogs.emotes',
    'cogs.sprite'
)


def _prefix_callable(bot, msg):
    return ['mush ', '!m ']


class Mushmom(commands.Bot):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(command_prefix=_prefix_callable)
        self.session = None  # set in on_ready
        self.reply_cache = io.ReplyCache(seconds=300)
        self.db = db.Database(db_client)

        # add global checks
        self.add_check(checks.not_bot)
        self.remove_command('help')

        # load extensions
        for ext in initial_extensions:
            self.load_extension(f'{__package__}.{ext}')

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')
        self.session = aiohttp.ClientSession(loop=self.loop)

        if not self._verify_cache_integrity.is_running:
            self._verify_cache_integrity.start()

    async def on_message(self, message):
        """
        Call emotes if no command and emote names are passed

        :param message:
        :return:
        """
        ctx = await self.get_context(message)

        # not handled by other commands
        if (ctx.prefix and not ctx.command
                and all([await check(ctx) for check in self._checks])):
            args = message.content[len(ctx.prefix):].split(' ')
            cmd = args.pop(0)

            # manually try to call as emote command
            if cmd not in resources.EMOTIONS:
                return

            command = self.get_command('emote')
            if not command:  # not loaded
                return
            else:
                ctx.command = command

            if args:  # handle TooManyArguments manually
                error = commands.TooManyArguments()
                await self.on_command_error(ctx, error)
            else:
                try:
                    await ctx.invoke(command, emote=cmd)
                except commands.CommandError as error:
                    await self.on_command_error(ctx, error)
        else:
            await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """
        Overwrite default to always run. Searches for error in cogs.ref.ERRORS,
        which is a nested dict

        :param ctx:
        :param error:
        :return:
        """
        if ctx in self.reply_cache:  # already sent message
            self.reply_cache.remove(ctx)
            return

        cmd = ctx.command.qualified_name
        cog = ctx.cog.qualified_name.lower()
        err_ns = ('errors' if isinstance(error, errors.MushmomError)
                  else 'commands')
        err = f'{err_ns}.{error.__class__.__name__}'

        try:  # search for error
            specs = ref.ERRORS[cog][cmd][err]
            msg, ref_cmds = specs.values()
        except KeyError:  # not defined
            e = error
            print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            return

        await self.send_error(ctx, msg, ref_cmds)

    def get_emoji_url(self, emoji_id):
        """
        Convenience wrapper to pull url from emoji

        :param emoji_id:
        :return:
        """
        emoji = self.get_emoji(emoji_id)

        if emoji:
            return emoji.url
        else:
            warnings.warn(f'Emoji<{emoji_id}> was not found', ResourceWarning)
            return self.user.avatar_url  # fall back on profile pic

    async def send_error(self, ctx, text=None, ref_cmds=None,
                         delete_message=not config.core.debug,
                         delay=config.core.default_delay):
        """
        Generic function to send formatted error.  Deletion will not happen
        when DEBUG is on

        :param ctx:
        :param text:
        :param ref_cmds:
        :param delete_message:
        :param delay:
        :return:
        """
        # defaults
        if text is None:
            text = 'Mushmom failed *cry*'

        if ref_cmds is None:
            ref_cmds = []

        # send error
        embed = discord.Embed(description=text,
                              color=config.core.embed_color)
        embed.set_author(name='Error', icon_url=ctx.bot.user.avatar_url)
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

    @tasks.loop(minutes=10)
    async def _verify_cache_integrity(self):
        """
        Clean up stray cached replies

        :return:
        """
        self.reply_cache.verify_cache_integrity()

    async def close(self):
        await super().close()
        await self.session.close()
        self.db_client.close()
