"""
Character commands

"""
import discord
import asyncio
import inspect

from discord.ext import commands
from typing import Optional

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import errors, converters


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def list_chars(self, ctx, user, text, thumbnail=None):
        """
        List users chars. Returns user and prompt

        :param ctx:
        :param text:
        :param thumbnail:
        :param reply: if message sent as reply or not
        :param user: db user if already retrieved
        :return:
        """
        embed = discord.Embed(description=text, color=config.core.embed_color)
        embed.set_author(name='Characters', icon_url=self.bot.user.avatar_url)

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

    async def select_char(self, ctx, user, text=''):
        """
        Sends embed with list of chars.  User should react to select

        :param ctx:
        :param text:
        :param user: db user if already retrieved
        :return:
        """
        thumbnail = self.bot.get_emoji_url(config.emojis.mushping)
        msg = (f'{text}React to select a character or select '
               f'\u200b \u274e \u200b to cancel\n\u200b')
        prompt = await self.list_chars(ctx, user, msg, thumbnail)

        # numbered unicode emojis 1 - # max chars
        reactions = {f'{x + 1}': f'{x + 1}\ufe0f\u20e3'
                     for x in range(min(len(user['chars']), config.core.max_chars))}
        reactions['x'] = '\u274e'

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
            if not config.core.debug:
                await prompt.delete()  # clean up prompt

            raise errors.TimeoutError  # handle in command errors

        sel = next(k for k, v in reactions.items() if reaction.emoji == v)

        return prompt, sel

    async def get_char_index(self, ctx, user, name=None, desc='',
                             cancel_text='Cancelled'):
        """
        Get index from char list

        :param ctx:
        :param user:
        :param name:
        :param desc: text to add before instructions
        :param cancel_text:
        :return:
        """
        chars = user['chars']

        if name:
            ind = next((i for i, x in enumerate(chars)
                        if x['name'] == name), None)

            if ind is None:
                raise errors.DataNotFound
        else:
            prompt, sel = await self.select_char(ctx, user)

            # cache in case need to clean up
            self.bot.reply_cache.add(ctx, prompt)

            if sel == 'x':
                await ctx.send(cancel_text)
                ind = None
            else:
                ind = int(sel)-1

        return ind

    @commands.command()
    async def chars(self, ctx):
        user = await db.get_user(ctx.author.id)
        await self.list_chars(ctx, user, 'Your mushable characters\n\u200b')

    @commands.group(alias='select')
    async def set(self, ctx):
        pass

    @set.command(name='main', aliases=['default'])
    async def _main(self, ctx, name: Optional[str] = None):
        user = await db.get_user(ctx.author.id)

        if not user or not user['chars']:  # no characters
            raise errors.NoMoreItems

        cancel_text = 'Your main was not changed'
        new_i = await self.get_char_index(ctx, user, name,
                                          cancel_text=cancel_text)

        if new_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
            return

        ret = await db.set_user(ctx.author.id, {'default': new_i})

        if ret.acknowledged:
            name = user['chars'][new_i]['name']
            await ctx.send(f'Your main was changed to **{name}**')
        else:
            raise errors.DataWriteError

        # no error, release from cache
        self.bot.reply_cache.remove(ctx)

    @commands.command()
    async def delete(self, ctx, name: Optional[str] = None):
        user = await db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        curr_i = user['default']
        cancel_text = 'Deletion cancelled'
        del_i = await self.get_char_index(ctx, user, name,
                                          cancel_text=cancel_text)

        if del_i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
            return

        # remove char and handle default
        if del_i > curr_i:
            new_i = curr_i
        elif del_i < curr_i:
            new_i = curr_i - 1
        else:
            new_i = 0  # if deleted main, default to first

        char = user['chars'].pop(del_i)
        ret = await db.set_user(ctx.author.id, {'default': new_i,
                                                'chars': user['chars']})

        if ret.acknowledged:
            await ctx.send(f'**{char["name"]}** was deleted')
        else:
            raise errors.DataWriteError

        self.bot.reply_cache.remove(ctx)

    @commands.command(ignore_extra=False)
    async def rename(self, ctx,
                     name: Optional[converters.CharNameConverter] = None,
                     new_name=None):
        """
        Rename char

        Use ignore_extra=False because otherwise may incorrectly capture
        new_name as name

        e.g.
        mush rename not_a_char_name Mushmom
        - new_name = not_a_char_name

        :param ctx:
        :param name:
        :param new_name:
        :return:
        """
        if not new_name:
            raise commands.MissingRequiredArgument(
                inspect.Parameter('new_name', inspect.Parameter.POSITIONAL_ONLY)
            )

        user = await db.get_user(ctx.author.id)

        if not user or not user['chars']:
            raise errors.NoMoreItems

        desc = ('Character was not found. '
                f'\u200b Who should be renamed **{new_name}**?')
        cancel_text = 'No character was renamed'
        i = await self.get_char_index(ctx, user, name, desc, cancel_text)

        if i is None:  # cancelled
            self.bot.reply_cache.remove(ctx)
            return

        _name = user['chars'][i]['name']
        user['chars'][i]['name'] = new_name
        ret = await db.set_user(ctx.author.id, {'chars': user['chars']})

        if ret.acknowledged:
            await ctx.send(f'**{_name}** was renamed **{new_name}**')
        else:
            raise errors.DataWriteError

    async def cog_after_invoke(self, ctx):
        # unregister reply cache if successful
        if not ctx.command_failed:
            self.bot.reply_cache.remove(ctx)

    async def cog_command_error(self, ctx, error):
        # clean up stray replies
        if not ctx.command.has_error_handler():
            await self.bot.reply_cache.clean_up(ctx)


def setup(bot):
    bot.add_cog(Characters(bot))
