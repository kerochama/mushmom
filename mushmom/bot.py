import discord
import os
import aiohttp
import warnings

from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime

from mushmom import config
from mushmom.utils import checks, io
from mushmom.mapleio import resources


load_dotenv()  # use env variables from .env

initial_extensions = (
    'cogs.core',
    'cogs.meta',
    'cogs.characters',
    'cogs.import',
    'cogs.emotes',
    'cogs.sprite'
)


class Mushmom(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None  # set in on_ready
        self.reply_cache = io.ReplyCache(seconds=300)

        # add global checks
        self.add_check(checks.not_bot)

        # load extensions
        for ext in initial_extensions:
            self.load_extension(ext)

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')
        self.session = aiohttp.ClientSession(loop=self.loop)

        if not self.verify_cache_integrity.is_running:
            self.verify_cache_integrity.start()

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

            if cmd in resources.EMOTIONS:  # manually call as emote command
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
    async def verify_cache_integrity(self):
        """
        Clean up stray cached replies

        :return:
        """
        self.reply_cache.verify_cache_integrity()

    async def close(self):
        await super().close()
        await self.session.close()


if __name__ == "__main__":
    bot = Mushmom(command_prefix=['mush ', '!m '])
    bot.run(os.getenv('TOKEN'))
