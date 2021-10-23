"""
Character commands

"""
import discord

from discord.ext import commands
from typing import Optional

from .utils import errors, prompts


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def chars(self, ctx: commands.Context) -> None:
        """
        List all characters registered

        Parameters
        ----------
        ctx: commands.Context

        """
        user = await self.bot.db.get_user(ctx.author.id)

        if not user:
            raise errors.NoMoreItems

        msg = 'Your mushable characters\n\u200b'
        await prompts.list_chars(ctx, user, msg)

    @commands.command(aliases=['rr'])
    async def reroll(
            self,
            ctx: commands.Context,
            name: Optional[str] = None
    ) -> None:
        """
        Switch your main character when using emotes/sprites to the
        character specified.  If no character name is provided, a
        reactable prompt of registered characters will appear for
        selection

        Parameters
        ----------
        ctx: commands.Context
        name: Optional[str]
            the character's name. If none, send prompt

        """
        user = await self.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:  # no characters
            raise errors.NoMoreItems

        new_i = await prompts.get_char(ctx, user, name=name)

        if new_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx.message)
            await ctx.send('Your main was not changed')
            return

        ret = await self.bot.db.set_user(ctx.author.id, {'default': new_i})

        if ret.acknowledged:
            name = user['chars'][new_i]['name']
            await ctx.send(f'Your main was changed to **{name}**')
        else:
            raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx.message)

    @commands.command()
    async def delete(
            self,
            ctx: commands.Context,
            name: Optional[str] = None
    ) -> None:
        """
        Delete the specified character from registry. If no character
        name is provided, a reactable prompt of registered characters
        will appear for selection

        Parameters
        ----------
        ctx: commands.Context
        name: Optional[str]
            the character's name. If none, send prompt

        """
        user = await self.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        curr_i = user['default']
        del_i = await prompts.get_char(ctx, user, name=name)

        if del_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx.message)
            await ctx.send('Deletion cancelled')
            return

        # remove char and handle default
        if del_i > curr_i:
            new_i = curr_i
        elif del_i < curr_i:
            new_i = curr_i - 1
        else:
            new_i = 0  # if deleted main, default to first

        char = user['chars'].pop(del_i)
        update = {'default': new_i, 'chars': user['chars']}
        ret = await self.bot.db.set_user(ctx.author.id, update)

        if ret.acknowledged:
            await ctx.send(f'**{char["name"]}** was deleted')
        else:
            raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx.message)

    @commands.command()
    async def rename(
            self,
            ctx: commands.Context,
            name: str,
            new_name: str
    ) -> None:
        """
        Rename a character with the new name given

        Parameters
        ----------
        ctx: commands.Context
        name: str
            the character's name. If none, send prompt
        new_name: str
            new character name

        """
        user = await self.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        # check if new_name exists
        chars = user['chars']
        _iter = (c['name'] for c in chars if c['name'] == new_name)
        exists = next(_iter, None)

        if exists:
            raise errors.CharacterAlreadyExists

        # get char to replace
        i = await prompts.get_char(ctx, user, name=name)

        chars[i]['name'] = new_name
        update = {'chars': chars}
        ret = await self.bot.db.set_user(ctx.author.id, update)

        if ret.acknowledged:
            await ctx.send(f'**{name}** was renamed **{new_name}**')
        else:
            raise errors.DataWriteError

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
    bot.add_cog(Characters(bot))
