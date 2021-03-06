"""
Emote related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from .. import config, mapleio
from .utils import converters, errors
from .resources import EMOJIS


class Emotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def emote(
            self,
            ctx: commands.Context,
            emote: Optional[converters.EmotionConverter] = None,
            *,
            options: converters.ImgFlags
    ) -> None:
        """
        Replace message with the emote specified. For a list of usable
        emotes, see `{prefix}emotes`

        Parameters
        ----------
        ctx: commands.Context
        emote: Optional[str]
            a word listed in in emotions.json
        options: converters.ImgFlags
            --char, -c: character to use

        """
        name = options.char.name or "char"
        emote = emote or options.char.emotion

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(EMOJIS['mushloading']) or '\u23f3'
        react_task = self.bot.loop.create_task(
            self.bot.add_delayed_reaction(ctx, emoji)
        )

        # create emote
        data = await mapleio.api.get_emote(
            options.char, emotion=emote, session=self.bot.session)
        react_task.cancel()  # no need to send if it gets here first

        if data:
            if not config.core.debug:
                try:
                    await ctx.message.delete()  # delete original message
                except commands.MissingPermissions:
                    pass

            filename = f'{name}_{emote}.png'
            img = discord.File(fp=BytesIO(data), filename=filename)
            await self.bot.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @commands.command()
    async def emotes(self, ctx: commands.Context) -> None:
        """
        List all emotes available

        Parameters
        ----------
        ctx: commands.Context

        """
        embed = discord.Embed(
            description='The following is a list of emotes you can use\n\u200b',
            color=config.core.embed_color
        )

        embed.set_author(name='Emotes', icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji_url(EMOJIS['mushheart'])
        embed.set_thumbnail(url=thumbnail)

        # split emotions into 3 lists (order not preserved)
        emotes = [mapleio.resources.EMOTIONS[i::3] for i in range(3)]
        embed.add_field(name='Emotes', value='\n'.join(emotes[0]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[1]))
        embed.add_field(name='\u200b', value='\n'.join(emotes[2]))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Emotes(bot))
