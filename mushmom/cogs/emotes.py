"""
Emote related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from .. import config
from ..utils import converters, errors
from ..mapleio import api, resources
from ..mapleio.character import Character


class Emotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(ignore_extra=False)
    async def emote(self, ctx,
                    emote: Optional[converters.EmotionConverter] = 'default'):
        """
        Replace message with the emote specified. For a list of usable
        emotes, see `{prefix}emotes`

        Use ignore_extra=False to differentiate improper emotes from default
        emote (can be used directly without args)

        :param ctx:
        :param emote:
        :return:
        """
        # grab character
        char_data = await self.bot.db.get_char_data(ctx.author.id)

        if not char_data:
            raise errors.DataNotFound

        char = Character.from_json(char_data)
        name = char.name or "char"

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(config.emojis.mushloading) or '\u23f3'
        react_task = self.bot.loop.create_task(
            self.bot.add_delayed_reaction(ctx, emoji)
        )

        # create emote
        data = await api.get_emote(char, emotion=emote,
                                   session=self.bot.session)
        react_task.cancel()  # no need to send if it gets here first

        if data:
            if not config.core.debug:
                await ctx.message.delete()  # delete original message

            filename = f'{name}_{emote}.png'
            img = discord.File(fp=BytesIO(data), filename=filename)
            await self.bot.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @commands.command()
    async def emotes(self, ctx):
        """
        List all emotes available

        :param ctx:
        :return:
        """
        embed = discord.Embed(
            description='The following is a list of emotes you can use\n\u200b',
            color=config.core.embed_color
        )

        embed.set_author(name='Emotes', icon_url=self.bot.user.avatar_url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushheart)
        embed.set_thumbnail(url=thumbnail)

        # split emotions into 3 lists
        emotes = [resources.EMOTIONS[i::3] for i in range(3)]  # order not preserved
        embed.add_field(name='Emotes', value='\n'.join(emotes[0]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[1]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[2]))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Emotes(bot))
