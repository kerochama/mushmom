import discord
import os
import aiohttp
import warnings

from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime

from mushmom import config
from mushmom.utils import checks
from mushmom.mapleio import states

load_dotenv()  # use env variables from .env

initial_extensions = (
    'cogs.core',
    'cogs.meta',
    'cogs.characters',
    'cogs.import',
    'cogs.emotes',
    'cogs.sprite'
)


class ReplyCache:
    def __init__(self, timeout=300):
        """
        Maintains a cache of messages sent by bot in response to a command
        so that they can be referenced/cleaned subsequently

        :param timeout: seconds passed signifying can be deleted
        """
        # keep track of message replies to clean up when error
        # does not have to be a direct reply, just response to command
        self._reply_cache = {
            # message.id: [(reply, ts)]
        }
        self.timeout = timeout  # seconds

    def register(self, ctx, reply):
        msg_id = ctx.message.id
        record = (reply, datetime.utcnow())

        if msg_id in self._reply_cache:
            self._reply_cache[msg_id].append(record)
        else:
            self._reply_cache[msg_id] = [record]

    def unregister(self, ctx):
        return self._reply_cache.pop(ctx.message.id, None)

    def clean(self, ctx, delete=not config.core.debug):
        """
        Try to delete and remove from cache

        :param ctx:
        :param delete:
        :return:
        """
        replies = self.unregister(ctx) or []

        if not delete:
            return

        for reply, ts in replies:
            try:
                reply.delete()
            except discord.HTTPException:
                pass

    def run_garbage_collector(self):
        """
        Loop through cache and remove anything older than timeout

        :return:
        """
        # clean each list
        for msg_id, replies in self._reply_cache.items():
            cleansed = [(reply, ts) for reply, ts in replies
                        if (datetime.utcnow() - ts).seconds <= self.timeout]
            self._reply_cache[msg_id] = cleansed

        # clean dict
        for msg_id in list(self._reply_cache.keys()):
            if not self._reply_cache[msg_id]:  # empty list
                del self._reply_cache[msg_id]


class Mushmom(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None  # set in on_ready
        self.reply_cache = ReplyCache()

        # add global checks
        self.add_check(checks.not_bot)

        # load extensions
        for ext in initial_extensions:
            self.load_extension(ext)

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')
        self.session = aiohttp.ClientSession(loop=self.loop)

        if not self.run_garbage_collector.is_running:
            self.run_garbage_collector.start()

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

            if cmd in states.EMOTIONS:  # manually call as emote command
                emotes_cog = self.get_cog('Emotes')

                if emotes_cog:  # emote cog exists
                    if args:  # handle TooManyArguments manually
                        error = commands.TooManyArguments()
                        await emotes_cog.emote_error(ctx, error)
                    else:
                        try:
                            await emotes_cog.emote(ctx, cmd)
                        except commands.CommandError as e:
                            await emotes_cog.emote_error(ctx, e)
        else:
            await self.process_commands(message)

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

    @tasks.loop(minutes=10)
    async def run_garbage_collector(self):
        """
        Clean up stray cached replies

        :return:
        """
        self.reply_cache.run_garbage_collector()

    async def close(self):
        await super().close()
        await self.session.close()


if __name__ == "__main__":
    bot = Mushmom(command_prefix=['mush ', '!m '])
    bot.run(os.getenv('TOKEN'))
