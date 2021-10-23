"""
Import character commands

"""
import discord
import inspect

from discord.ext import commands
from typing import Optional

from .. import config
from .utils import converters, errors, prompts
from ..mapleio.character import Character


class Import(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='import', aliases=['add'])
    async def _import(
            self,
            ctx: commands.Context,
            name: converters.NotMapleIOURLConverter,
            url: Optional[converters.MapleIOURLConverter] = None
    ) -> None:
        """
        Register a new character. Requires either a
        `http://maplestory.io/api/character` url or a JSON file defining
        character data, both of which can be retrieved from `maples.im`
        or `beta.maplestory.studio`.  To get the url, right click your
        character and click "Copy Image Address".  The JSON file can be
        generated by exporting your character from either website.

        Parameters
        ----------
        ctx: commands.Context
        name: Optional[str]
            name of character to import
        url: Optional[str]:
            http://maplestory.io/api/character url with character data
        [attachment: JSON file]
            JSON file containing character data

        """
        # Must supply source data
        if not (url or ctx.message.attachments):
            raise commands.MissingRequiredArgument(
                inspect.Parameter('url', inspect.Parameter.POSITIONAL_ONLY)
            )

        # parse char data
        if url:  # maplestory.io char api
            parser, src = Character.from_url, url
        elif ctx.message.attachments:  # json output of sim and studio
            json_file = next((att for att in ctx.message.attachments
                              if att.filename[-5:] == '.json'), None)

            if not json_file:
                raise errors.UnexpectedFileTypeError

            # get json
            data = await self.bot.download(json_file.url, errors.DiscordIOError)
            parser, src = Character.from_json, data
        try:
            char = parser(src)
        except Exception:
            raise errors.CharacterParseError

        char.name = name

        # query database
        user = await self.bot.db.get_user(ctx.author.id)

        if not user:  # new user
            ret = await self.bot.db.add_user(ctx.author.id, char.to_dict())
        else:
            # check if char exists
            chars = user['chars']
            _iter = (i for i, c in enumerate(chars) if c['name'] == name)
            i = next(_iter, None)

            if i is not None:  # exists; prompt if want to replace
                text = f'**{name}** already exists. Replace?'
                replace = await prompts.confirm_prompt(ctx, text)
                chars[i] = char.to_dict()

                if not replace:
                    await ctx.send(f'{name} was **not** replaced')
                    return
            elif len(user['chars']) < config.core.max_chars:
                chars.append(char.to_dict())
            else:  # too many chars; replace?
                text = (f'{config.core.bot_name} can only save '
                        f'{config.core.max_chars} character'
                        f'{"s" if config.core.max_chars > 1 else ""}. \u200b '
                        'Choose a character to replace.')
                i = await prompts.get_char(ctx, user, text)

                if i is None:
                    self.bot.reply_cache.remove(ctx.message)  # clean up select prompt
                    await ctx.send(f'**{name}** was not saved')
                    return
                else:
                    chars[i] = char.to_dict()

            # update database
            update = {'chars': chars}
            ret = await self.bot.db.set_user(ctx.author.id, update)

        if ret:
            if ret.acknowledged:
                await ctx.send(f'**{name}** has been successfully mushed')
            else:
                raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx.message)

    @_import.error
    async def _import_error(
            self,
            ctx: commands.Context,
            error: Exception
    ) -> None:
        """
        Local import error handler for MissingRequiredArgument, which
        has specific logic based on which parameter is missing.

        Parameters
        ----------
        ctx: commands.Context
        error: Exception

        """
        # clean up orphaned prompts
        await self.bot.reply_cache.clean_up(ctx.message)

        if not isinstance(error, commands.MissingRequiredArgument):
            return  # other handles handled normally

        if error.param.name == 'name':
            msg = 'Supply a character name to start mushing. See:\n\u200b'
        elif error.param.name == 'url':
            msg = 'Missing source data. Please use:\n\u200b'

        err = await self.bot.send_error(ctx, msg, ref_cmds=['import'])
        self.bot.reply_cache.add(ctx.message, err)  # stop default error handler

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        # unregister reply cache if successful
        if not ctx.command_failed:
            self.bot.reply_cache.remove(ctx.message)

    async def cog_command_error(
            self,
            ctx: commands.Context,
            error: Exception
    ) -> None:
        # clean up stray replies
        if not ctx.command.has_error_handler():
            await self.bot.reply_cache.clean_up(ctx.message)


def setup(bot):
    bot.add_cog(Import(bot))
