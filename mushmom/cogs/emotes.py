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
                    emote: Optional[converters.EmotionConverter] = 'default'):
        # grab character
        char_data = await db.get_char_data(ctx.author.id)

        if not char_data:
            raise errors.DataNotFound

        char = Character.from_json(char_data)
        name = char.name or "char"

        # create emote
        data = await api.get_emote(char, emotion=emote)

        if data:
            if not config.DEBUG:
                await ctx.message.delete()  # delete original message

            filename = f'{name}_{emote}.png'
            img = discord.File(fp=BytesIO(data), filename=filename)
            await webhook.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @emote.error
    async def emote_error(self, ctx, error):
        msg = None
        cmds = None

        if isinstance(error, commands.TooManyArguments):
            msg = 'Emote not found. \u200b See:\n\u200b'
            cmds = {
                'Commands': f'`{self.bot.command_prefix[0]}emotes list`'
            }
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


def setup(bot):
    bot.add_cog(Emotes(bot))
