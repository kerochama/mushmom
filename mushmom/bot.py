import discord
import os
import aiohttp
import inspect

from discord.ext import commands
from io import BytesIO
from dotenv import load_dotenv
from typing import Optional

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import checks, errors, webhook, converters, io
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character

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
        self.reply_cache = errors.ReplyCache(garbage_collect_after=50)

        # attach some default commands
        self.add_cog(Core(self))

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')

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


def setup_bot():
    bot = Mushmom(command_prefix=['mush ', '!m '])
    bot.add_check(checks.not_bot)
    bot.load_extension('cogs.characters')
    bot.load_extension('cogs.emotes')
    bot.load_extension('cogs.import')
    bot.load_extension('cogs.sprite')

    return bot


bot = setup_bot()


@bot.group()
async def emotes(ctx):
    pass


@emotes.command(name='list')
async def _list(ctx):
    embed = discord.Embed(
        description='The following is a list of emotes you can use\n\u200b',
        color=config.EMBED_COLOR
    )

    embed.set_author(name='Emotes', icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=config.EMOJIS['mushheart'])

    # split emotions into 3 lists
    emotes = [states.EMOTIONS[i::3] for i in range(3)]  # order not preserved
    embed.add_field(name='Emotes', value='\n'.join(emotes[0]))
    embed.add_field(name='\u200b', value='\n'.join(emotes[1]))
    embed.add_field(name='\u200b', value='\n'.join(emotes[2]))

    await ctx.send(embed=embed)


if __name__ == "__main__":
    # bot = setup_bot()
    bot.run(os.getenv('TOKEN'))
