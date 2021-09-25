"""
Emote related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import converters, errors, webhook
from mushmom.mapleio import api
from mushmom.mapleio.character import Character


class Emotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(ignore_extra=False)
    async def emote(self, ctx,
                    emotion: Optional[converters.EmotionConverter] = 'default'):
        # grab character
        char_data = await db.get_char_data(ctx.author.id)

        if not char_data:
            raise errors.DataNotFound

        char = Character.from_json(char_data)
        name = char.name or "char"

        # create emote
        data = await api.get_emote(char, emotion=emotion)

        if data:
            if not config.DEBUG:
                await ctx.message.delete()  # delete original message

            img = discord.File(fp=BytesIO(data), filename=f'{name}_{emotion}.png')
            await webhook.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @emote.error
    async def emote_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            msg = 'Emote not found. \u200b See:\n\u200b'
            fields = {
                'Commands': f'`{self.bot.command_prefix[0]}emotes list`'
            }
        elif isinstance(error, errors.DataNotFound):
            msg = 'No registered character. \u200b See:\n\u200b'
            fields = {'Commands': f'`{self.bot.command_prefix[0]}import`'}
        elif isinstance(error, errors.MapleIOError):
            msg = 'Could not get maple data. \u200b Try again later'
            fields = None

        if msg:
            await errors.send(ctx, msg, fields=fields)


def setup(bot):
    bot.add_cog(Emotes(bot))
