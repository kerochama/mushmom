"""
Commands pertaining to the bot itself

"""
import discord

from discord.ext import commands

from .. import config
from .resources import EMOJIS, ATTACHMENTS


class Self(commands.Cog, name=config.core.bot_name):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        """
        Say hello!

        Parameters
        ----------
        ctx: commands.Context

        """
        await ctx.send('hai')

    @commands.command()
    async def about(self, ctx: commands.Context) -> None:
        """
        Get some info about Mushmom

        Parameters
        ----------
        ctx: commands.Context

        """
        embed = discord.Embed(
            description=('Mushmom is a bot that will send emotes and actions '
                         'for you. For a more in-depth explanation, demos, '
                         f'and more, go to {config.website.url}'),
            color=config.core.embed_color
        )

        embed.set_author(name=f'About {config.core.bot_name}',
                         icon_url=self.bot.user.display_avatar.url)

        thumbnail = self.bot.get_emoji_url(EMOJIS['mushparty'])
        embed.set_thumbnail(url=thumbnail)
        img = self.bot.get_attachment_url(*ATTACHMENTS['mushmomheader'])
        embed.set_image(url=img)

        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx: commands.Context) -> None:
        """
        Get public invite link

        Parameters
        ----------
        ctx: commands.Context

        """
        await ctx.send(f'{config.discord.invite}')

    @commands.command()
    async def version(self, ctx: commands.Context) -> None:
        """
        Get the current bot version

        Parameters
        ----------
        ctx: commands.Context

        """
        await ctx.send(f'v{config.core.version}')


def setup(bot):
    bot.add_cog(Self(bot))
