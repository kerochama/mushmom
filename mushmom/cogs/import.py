"""
Import character commands

"""
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

    @commands.command(name='import', aliases=['add'])
    async def _import(self, ctx, name: converters.ImportNameConverter,
                      url: Optional[converters.MapleIOURLConverter] = None):
        # parse char data
        if url:  # maplestory.io char api
            char = Character.from_url(url)
        elif ctx.message.attachments:  # json output of sim and studio
            json_file = next((att for att in ctx.message.attachments
                              if att.filename[-5:] == '.json'), None)

            if not json_file:
                raise errors.UnexpectedFileTypeError

            # get json
            async with self.bot.session.get(json_file.url) as r:
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
        elif len(user['chars']) < config.core.max_chars:
            user['chars'].append(char.to_dict())
            ret = await db.set_user(ctx.author.id, {'chars': user['chars']})
        else:
            chars_cog = self.bot.get_cog('Characters')

            if not chars_cog:
                raise errors.MissingCogError

            text = (f'{config.core.bot_name} can only save '
                    f'{config.core.max_chars} character'
                    f'{"s" if config.core.max_chars > 1 else ""}. \u200b '
                    'Choose a character to replace.')
            prompt, sel = await chars_cog.select_char(ctx, user, text)

            # cache in case need to clean up
            self.bot.reply_cache.add(ctx, prompt)

            if sel == 'x':
                await ctx.send(f'**{name}** was not saved')
                ret = None
            else:
                user['chars'][int(sel) - 1] = char.to_dict()
                ret = await db.set_user(ctx.author.id, {'chars': user['chars']})

        if ret:
            if ret.acknowledged:
                await ctx.send(f'**{name}** has been successfully mushed')
            else:
                raise errors.DataWriteError

        # could have been cached in select_char
        self.bot.reply_cache.remove(ctx)

    @_import.error
    async def _import_error(self, ctx, error):
        # clean up orphaned prompts
        await self.bot.reply_cache.clean_up(ctx)

        if not isinstance(error, commands.MissingRequiredArgument):
            return  # other handles handled normally

        if error.param.name == 'name':
            msg = 'Supply a character name to start mushing! Try:\n\u200b'
        elif error.param.name == 'url':
            msg = 'Missing source data. Try:\n\u200b'

        ref_cmds = ['import']

        # format ref_cmds
        help_cog = self.bot.get_cog('Help')
        if help_cog:
            signatures = help_cog.get_signatures(ctx, ref_cmds or [])
            cmds = {'Commands': '\n'.join(signatures)} if signatures else None
        else:  # skip cmd help
            cmds = None

        err = await errors.send(ctx, msg, fields=cmds)
        self.bot.reply_cache.add(ctx, err)  # stop default error handler

    async def cog_after_invoke(self, ctx):
        # unregister reply cache if successful
        if not ctx.command_failed:
            self.bot.reply_cache.remove(ctx)

    async def cog_command_error(self, ctx, error):
        # clean up stray replies
        if not ctx.command.has_error_handler():
            await self.bot.reply_cache.clean_up(ctx)


def setup(bot):
    bot.add_cog(Import(bot))
