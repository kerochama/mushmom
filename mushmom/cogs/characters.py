"""
Character commands

"""
import discord
import asyncio
import inspect

from discord.ext import commands
from typing import Optional, Union

from .. import config
from ..utils import errors, converters


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def list_chars(
            self,
            ctx: commands.Context,
            user: dict,
            text: str,
            thumbnail: str = None
    ) -> discord.Message:
        """
        List users chars

        Parameters
        ----------
        ctx: commands.Context
        user: dict
            user data from database
        text: str
            description displayed in embed
        thumbnail: str
            url to the embed thumbnail

        Returns
        -------
        discord.Message
            the message, if sent

        """
        embed = discord.Embed(description=text, color=config.core.embed_color)
        embed.set_author(name='Characters', icon_url=self.bot.user.avatar.url)

        if not thumbnail:
            thumbnail = self.bot.get_emoji_url(config.emojis.mushparty)

        embed.set_thumbnail(url=thumbnail)

        # format char names
        char_names = ['-'] * config.core.max_chars

        for i, char in enumerate(user['chars']):
            template = '**{} (default)**' if i == user['default'] else '{}'
            char_names[i] = template.format(char['name'])

        # full width numbers
        char_list = [f'{chr(65297 + i)} \u200b {name}'
                     for i, name in enumerate(char_names)]

        embed.add_field(name='Characters', value='\n'.join(char_list))
        msg = await ctx.send(embed=embed)

        return msg

    async def select_char(
            self, ctx: commands.Context,
            user: dict,
            name: Optional[str] = None,
            text: Optional[str] = None
    ) -> Optional[int]:
        """
        Gets char index if name passed. Otherwise, sends embed with
        list of chars. User should react to select

        Parameters
        ----------
        ctx: commands.Context
        user: dict
            user data from database
        name: str
            the character to be found
        text:
            description displayed in embed prior to instructions

        Returns
        -------
        Optional[int]
            character index or None if cancelled

        """
        if name:
            chars = user['chars']
            char_iter = (i for i, x in enumerate(chars)
                         if x['name'].lower() == name.lower())
            ind = next(char_iter, None)

            if ind is None:
                raise errors.DataNotFound
            else:
                return ind

        # prompt if no name given
        thumbnail = self.bot.get_emoji_url(config.emojis.mushping)
        msg = (f'{text or ""}React to select a character or select '
               f'\u200b \u274e \u200b to cancel\n\u200b')
        prompt = await self.list_chars(ctx, user, msg, thumbnail)
        self.bot.reply_cache.add(ctx, prompt)  # cache for clean up

        # numbered unicode emojis 1 - # max chars
        max_chars = config.core.max_chars
        reactions = {f'{x + 1}': f'{x + 1}\ufe0f\u20e3'
                     for x in range(min(len(user['chars']), max_chars))}
        reactions['x'] = '\u274e'
        sel = await self.wait_for_reaction(ctx, prompt, reactions)

        return None if sel == 'x' else int(sel)-1

    @staticmethod
    async def wait_for_reaction(
            ctx: commands.Context,
            prompt: discord.Message,
            reactions: dict[str, Union[discord.Emoji, discord.PartialEmoji, str]]
    ) -> str:
        """
        Add reactions to message and wait for original author response

        Parameters
        ----------
        ctx: commands.Context
        prompt: discord.Message
            the message to which to add reactions
        reactions: dict[str, Union[discord.Emoji, discord.PartialEmoji, str]]
            key is meaning of reaction, value is the reaction

        Returns
        -------
        str
            the key value associated with selected reaction

        """
        # add reactions
        for reaction in reactions.values():
            await prompt.add_reaction(reaction)

        # wait for reaction
        try:
            reaction, user = (
                await ctx.bot.wait_for(
                    'reaction_add',
                    check=lambda r, u: (u == ctx.author
                                        and r.message.id == prompt.id
                                        and r.emoji in reactions.values()),
                    timeout=config.core.default_delay
                )
            )
        except asyncio.TimeoutError:
            raise errors.TimeoutError  # handle in command errors

        return next(k for k, v in reactions.items() if reaction.emoji == v)

    async def confirm_prompt(self, ctx: commands.Context, text) -> bool:
        """
        Prompt user for confirmation

        Parameters
        ----------
        ctx: commands.Context
        text: str
            text to display

        Returns
        -------
        bool
            user's selection

        """
        embed = discord.Embed(description=text, color=config.core.embed_color)
        embed.set_author(name='Confirmation', url=self.bot.user.avatar.url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushping)
        embed.set_thumbnail(url=thumbnail)
        prompt = ctx.send(embed=embed)
        self.bot.reply_cache.add(ctx, prompt)  # cache for clean up

        # wait for reaction
        reactions = {'true': '\u2705', 'false': '\u274e'}
        sel = await self.wait_for_reaction(ctx, prompt, reactions)

        return sel == 'true'  # other reactions will timeout

    @commands.command()
    async def chars(self, ctx: commands.Context) -> None:
        """
        List all characters registered

        Parameters
        ----------
        ctx: commands.Context

        """
        user = await self.bot.db.get_user(ctx.author.id)
        await self.list_chars(ctx, user, 'Your mushable characters\n\u200b')

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

        new_i = await self.select_char(ctx, user, name=name)

        if new_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
            await ctx.send('Your main was not changed')
            return

        ret = await self.bot.db.set_user(ctx.author.id, {'default': new_i})

        if ret.acknowledged:
            name = user['chars'][new_i]['name']
            await ctx.send(f'Your main was changed to **{name}**')
        else:
            raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx)

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
        del_i = await self.select_char(ctx, user, name=name)

        if del_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
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
        self.bot.reply_cache.remove(ctx)

    @commands.command(ignore_extra=False)
    async def rename(
            self,
            ctx: commands.Context,
            name: Optional[converters.CharNameConverter] = None,
            new_name: str = None
    ) -> None:
        """
        Rename a character with the new name give. The existing
        character name is optional, in which case a reactable prompt
        of registered characters will appear for selection

        Parameters
        ----------
        ctx: commands.Context
        name: Optional[str]
            the character's name. If none, send prompt
        new_name: str
            new character name

        Notes
        -----
        new_name would be populated by not_a_char_name without
        ignore_extra=False

        >>> mush rename not_a_char_name Mushmom

        """
        if not new_name:
            raise commands.MissingRequiredArgument(
                inspect.Parameter('new_name', inspect.Parameter.POSITIONAL_ONLY)
            )

        user = await self.bot.db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        text = ('Character was not found. '
                f'\u200b Who should be renamed **{new_name}**?')
        i = await self.select_char(ctx, user, name=name, text=text)

        if i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
            await ctx.send('No character was renamed')
            return

        _name = user['chars'][i]['name']
        user['chars'][i]['name'] = new_name
        update = {'chars': user['chars']}
        ret = await self.bot.db.set_user(ctx.author.id, update)

        if ret.acknowledged:
            await ctx.send(f'**{_name}** was renamed **{new_name}**')
        else:
            raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx)

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        # unregister reply cache if successful
        if not ctx.command_failed:
            self.bot.reply_cache.remove(ctx)

    async def cog_command_error(
            self,
            ctx: commands.Context,
            error: Exception
    ) -> None:
        # clean up stray replies
        if not ctx.command.has_error_handler():
            await self.bot.reply_cache.clean_up(ctx)


def setup(bot):
    bot.add_cog(Characters(bot))
