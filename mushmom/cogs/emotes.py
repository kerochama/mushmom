"""
Emote related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import converters, errors, io
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character


class Emotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(ignore_extra=False)
    async def emote(self, ctx,
                    emote: Optional[converters.EmotionConverter] = 'default'):
        # grab character
        char_data = await db.get_char_data(ctx.author.id)

        if not char_data:
            raise errors.DataNotFound

        char = Character.from_json(char_data)
        name = char.name or "char"

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(config.emojis.mushloading) or '\u23f3'
        react_task = self.bot.loop.create_task(io.delayed_reaction(ctx, emoji))

        # create emote
        data = await api.get_emote(char, emotion=emote,
                                   session=self.bot.session)
        react_task.cancel()  # no need to send if it gets here first

        if data:
            if not config.core.debug:
                await ctx.message.delete()  # delete original message

            filename = f'{name}_{emote}.png'
            img = discord.File(fp=BytesIO(data), filename=filename)
            await io.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @emote.error
    async def emote_error(self, ctx, error):
        msg = None
        cmds = None

        if isinstance(error, commands.TooManyArguments):
            msg = (f'No registered characters. \u200b To import '
                   ' one use:\n\u200b')
            cmds = {'Commands': '\n'.join([
                '`mush add [name] [url: maplestory.io]`',
                '`mush add [name]` with a JSON file attached',
                '`mush import [name] [url: maplestory.io]`',
                '`mush import [name]` with a JSON file attached',
            ])}
        elif isinstance(error, errors.MapleIOError):
            msg = 'Could not get maple data. \u200b Try again later'

        await errors.send(ctx, msg, fields=cmds)

        if msg is None:
            raise error

    @commands.command()
    async def emotes(self, ctx):
        embed = discord.Embed(
            description='The following is a list of emotes you can use\n\u200b',
            color=config.core.embed_color
        )

        embed.set_author(name='Emotes', icon_url=self.bot.user.avatar_url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushheart)
        embed.set_thumbnail(url=thumbnail)

        # split emotions into 3 lists
        emotes = [states.EMOTIONS[i::3] for i in range(3)]  # order not preserved
        embed.add_field(name='Emotes', value='\n'.join(emotes[0]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[1]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[2]))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Emotes(bot))
