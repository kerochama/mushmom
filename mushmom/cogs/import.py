"""
Import character commands

"""
import discord
import aiohttp
import inspect

from discord.ext import commands
from typing import Optional

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import converters, errors
from mushmom.mapleio.character import Character


class Import(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='import', ignore_extra=False)
    async def _import(self, ctx, name: converters.ImportNameConverter,
                      url: Optional[converters.MapleIOURLConverter] = ''):
        # parse char data
        if url:  # maplestory.io char api
            char = Character.from_url(url)
        elif ctx.message.attachments:  # json output of sim and studio
            json_file = next((att for att in ctx.message.attachments
                              if att.filename[-5:] == '.json'), None)

            if not json_file:
                raise errors.UnexpectedFileTypeError

            # get json
            async with aiohttp.ClientSession() as session:
                async with session.get(json_file.url) as r:
                    if r.status == 200:
                        data = await r.json()
                    else:
                        raise errors.DiscordIOError

            char = Character.from_json(data)
        else:
            # doesnt matter which param.  Handled in error message
            raise commands.MissingRequiredArgument(
                inspect.Parameter('url', inspect.Parameter.POSITIONAL_ONLY)
            )

        char.name = name

        # query database
        user = await db.get_user(ctx.author.id)

        if not user:  # new user
            ret = await db.add_user(ctx.author.id, char.to_dict())
        elif len(user['chars']) < config.MAX_CHARS:
            user['chars'].append(char.to_dict())
            ret = await db.set_user(ctx.author.id, {'chars': user['chars']})
        else:
            chars_cog = self.bot.get_cog('Characters')

            if not chars_cog:
                raise commands.ExtensionNotLoaded('Characters')

            text = (f'{config.BOT_NAME} can only save {config.MAX_CHARS} '
                    f'character{"s" if config.MAX_CHARS > 1 else ""}. \u200b'
                    'Choose a character to replace.')
            prompt, sel = await chars_cog.select_char(ctx, user, text)

            # cache in case need to clean up
            self.bot.reply_cache.register(ctx, prompt)

            if sel == 'x':
                await ctx.send(f'{name} was not saved')
                ret = None
            else:
                user['chars'][int(sel) - 1] = char.to_dict()
                ret = await db.set_user(ctx.author.id, {'chars': user['chars']})

        if ret:
            if ret.acknowledged:
                await ctx.send(f'{name} has been successfully mushed')
            else:
                raise errors.DataWriteError

        # could have been cached in select_char
        self.bot.reply_cache.unregister(ctx)

    @_import.error
    async def _import_error(self, ctx, error):
        # clean up orphaned prompts
        self.bot.reply_cache.clean(ctx)

        msg = None
        cmds = {
            'Commands': '\n'.join([
                '`mush import [name] [url: maplestory.io]`',
                '`mush import [name]` with a JSON file attached'
            ])
        }

        if isinstance(error, commands.TooManyArguments):
            msg = f'{config.BOT_NAME} did not understand. \u200b Try:\n\u200b'
        elif isinstance(error, commands.BadArgument):
            msg = ('You must supply a character name to start mushing!'
                   ' \u200b Try:\n\u200b')
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'name':
                msg = ('You must supply a character name to start mushing!'
                       ' \u200b Try:\n\u200b')
            elif error.param.name == 'url':
                msg = 'Missing source data. \u200b Try:\n\u200b'
        else:
            cmds = None

            if isinstance(error, errors.UnexpectedFileTypeError):
                msg = f'{config.BOT_NAME} only accepts JSON files'
            elif isinstance(error, errors.TimeoutError):
                msg = 'No character was selected'
            elif isinstance(error, errors.DiscordIOError):
                msg = (f'Error trying to read attached JSON file.'
                       '\u200b Try again later')
            elif isinstance(error, errors.DataWriteError):
                msg = 'Problem saving character. \u200b Try again later'

        await errors.send(ctx, msg, fields=cmds)

        if msg is None:
            raise error

    async def cog_after_invoke(self, ctx):
        # unregister reply cache if successful
        if not ctx.command_failed:
            self.bot.reply_cache.unregister(ctx)


def setup(bot):
    bot.add_cog(Import(bot))
