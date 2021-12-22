"""
Full sprite related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from .. import config, mapleio
from .utils import converters, errors
from .resources import EMOJIS


class Sprites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def sprite(
            self,
            ctx: commands.Context,
            emotion: Optional[converters.EmotionConverter] = None,
            pose: Optional[converters.PoseConverter] = None,
            *,
            options: converters.ImgFlags
    ) -> None:
        """
        Replace message with the emote specified. For a list of usable
        emotions and poses, see `{prefix}emotions` and `{prefix}poses`,
        respectively

        Parameters
        ----------
        ctx: commands.Context
        emotion: Optional[str]
            a word listed in in emotions.json. If None, use default
        pose: Optional[str]
            a word listed in in poses.json. If None, use default
        options: converters.ImgFlags
            --char, -c: character to use

        """
        name = options.char.name or "char"
        emotion = emotion or options.char.emotion
        pose = pose or options.char.pose

        # add loading reaction to confirm command is still waiting for api
        # default: hour glass
        emoji = self.bot.get_emoji(EMOJIS['mushloading']) or '\u23f3'
        react_task = self.bot.loop.create_task(
            self.bot.add_delayed_reaction(ctx, emoji)
        )

        # create sprite
        data = await mapleio.api.get_sprite(
            options.char, pose=pose, emotion=emotion, session=self.bot.session)
        react_task.cancel()

        if data:
            if not config.core.debug:
                try:
                    await ctx.message.delete()  # delete original message
                except commands.MissingPermissions:
                    pass

            img = discord.File(fp=BytesIO(data),
                               filename=f'{name}_{emotion}_{pose}.png')
            await self.bot.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @sprite.command()
    async def emotions(self, ctx: commands.Context) -> None:
        """
        List the emotions available for characters

        Parameters
        ----------
        ctx: commands.Context

        """
        embed = discord.Embed(
            description=('The following is a list of emotions you can use in the '
                         'generation of your emoji or sprite.\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name='Emotions', icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji_url(EMOJIS['mushheart'])
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text='[GMS v225]')

        # split emotions into 3 lists
        emotions = [mapleio.resources.EMOTIONS[i::3] for i in range(3)]  # order not preserved
        embed.add_field(name='Emotions', value='\n'.join(emotions[0]))
        embed.add_field(name='\u200b', value='\n'.join(emotions[1]))
        embed.add_field(name='\u200b', value='\n'.join(emotions[2]))

        await ctx.send(embed=embed)

    @sprite.command()
    async def poses(self, ctx: commands.Context) -> None:
        """
        List the poses available for characters

        Parameters
        ----------
        ctx: commands.Context

        """
        embed = discord.Embed(
            description=('The following is a list of poses you can use in the '
                         'generation of your emoji or sprite.\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name='Poses', icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.get_emoji_url(EMOJIS['mushdab']))
        embed.set_footer(text='[GMS v225]')
        embed.add_field(name='Pose',
                        value='\n'.join(mapleio.resources.POSES.keys()))
        embed.add_field(name='Value',
                        value='\n'.join(mapleio.resources.POSES.values()))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Sprites(bot))
