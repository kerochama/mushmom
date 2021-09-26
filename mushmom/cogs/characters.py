"""
Character commands

"""
import discord
import asyncio

from discord.ext import commands

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import errors


class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reply_cache = errors.ReplyCache()

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
        embed = discord.Embed(description=text, color=config.EMBED_COLOR)
        embed.set_author(name='Characters', icon_url=self.bot.user.avatar_url)

        if not thumbnail:
            thumbnail = config.EMOJIS['mushparty']

        embed.set_thumbnail(url=thumbnail)

        # format char names
        char_names = ['-'] * config.MAX_CHARS

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
        thumbnail = config.EMOJIS['mushping']
        msg = (f'{text}React to select a character or select '
               f'\u200b \u274e \u200b to cancel\n\u200b')
        prompt = await self.list_chars(ctx, user, msg, thumbnail)

        # numbered unicode emojis 1 - # max chars
        reactions = {f'{x + 1}': f'{x + 1}\ufe0f\u20e3'
                     for x in range(min(len(user['chars']), config.MAX_CHARS))}
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
                    timeout=config.DEFAULT_DELAY
                )
            )
        except asyncio.TimeoutError:
            if not config.DEBUG:
                await prompt.delete()  # clean up prompt

            raise errors.TimeoutError  # handle in command errors

        sel = next(k for k, v in reactions.items() if reaction.emoji == v)

        return prompt, sel

    @commands.command()
    async def chars(self, ctx):
        user = await db.get_user(ctx.author.id)
        await self.list_chars(ctx, user, 'Your mushable characters\n\u200b')

    @commands.group(aliases=['select', 'sel'])
    async def set(self, ctx):
        pass

    @set.command(aliases=['main'])
    async def default(self, ctx):
        user = await db.get_user(ctx.author.id)
        prompt, sel = await self.select_char(ctx, user)

        # cache in case need to clean up
        self.reply_cache.register(ctx, prompt)

        if sel == 'x':
            await ctx.send(f'Your main was not changed')
        else:
            ret = await db.set_user(ctx.author.id, {'default': int(sel)-1})

            if ret.acknowledged:
                name = user['chars'][int(sel)-1]['name']
                await ctx.send(f'Your main was changed to **{name}**')
            else:
                raise errors.DataWriteError

        # no error, release from cache
        self.reply_cache.unregister(ctx)

    @default.error
    async def default_error(self, ctx, error):
        if isinstance(error, errors.DataWriteError):
            msg = 'Problem saving settings. \u200b Try again later'
        elif isinstance(error, errors.TimeoutError):
            msg = 'No character was selected'
        else:
            msg = str(error)

        # clean up orphaned prompts
        self.reply_cache.clean(ctx)

        await errors.send_error(ctx, msg)


def setup(bot):
    bot.add_cog(Characters(bot))
