import discord
import os
import aiohttp

from discord.ext import commands
from dotenv import load_dotenv

from mushmom.utils import checks, errors
from mushmom.mapleio import states

load_dotenv()  # use env variables from .env


class Core(commands.Cog):
    def __init__(self, bot):
        """
        Basic core commands

        :param bot:
        """
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send('hai')


class Mushmom(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None  # set in on_ready
        self.reply_cache = errors.ReplyCache(garbage_collect_after=50)

        # attach some default commands
        self.add_cog(Core(self))

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')
        self.session = aiohttp.ClientSession(loop=self.loop)

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

    async def close(self):
        await super().close()
        await self.session.close()


def setup_bot():
    bot = Mushmom(command_prefix=['mush ', '!m '])
    bot.add_check(checks.not_bot)
    bot.load_extension('cogs.characters')
    bot.load_extension('cogs.emotes')
    bot.load_extension('cogs.import')
    bot.load_extension('cogs.sprite')

    return bot


if __name__ == "__main__":
    bot = setup_bot()
    bot.run(os.getenv('TOKEN'))
