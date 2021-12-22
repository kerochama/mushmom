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

    @commands.command()
    async def start(self, ctx: commands.Context) -> None:
        """
        Instructions for people to get started.

        Parameters
        ----------
        ctx: commands.Context

        """
        embed = discord.Embed(
            description=(f'{config.core.bot_name} will send emotes and '
                         f'actions for you. Type `{ctx.prefix}help '
                         '<command>` for more information on a command.\n\n'
                         f'`{ctx.prefix}[args]` without a command will call '
                         f'`{ctx.prefix}emote [args]`. For a full list of'
                         f' emotes, type `{ctx.prefix}emotes`\n\u200b\n'),
            color=config.core.embed_color,
            url=config.website.url + '#get-started'
        )

        embed.set_author(name=f'{config.core.bot_name} Get Started',
                         icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji_url(EMOJIS['mushparty'])
        embed.set_thumbnail(url=thumbnail)
        img = self.bot.get_attachment_url(*ATTACHMENTS['mushmomheader'])
        embed.set_image(url=img)

        embed.add_field(
            name='Get Started',
            value=(':one: Create your character using '
                   '[maplestory.studio](https://maplestory.studio) or '
                   '[maples.im](https://maples.im)\n'
                   ':two: On a desktop, right click the sprite and select `Copy '
                   'Image Address`. For mobile, long-press the download button'
                   ' and copy the address that way\n'
                   f':three: Use the `{ctx.prefix}import [char name] [url]` '
                   'command with the url you just copied\n'
                   ':four: The bot should respond with a success message and you '
                   'can begin using emotes, actions, etc.\n\nFor more detailed'
                   ' instructions, you can check out [Get Started]'
                   f'({config.website.url + "#get-started"})\n\u200b'),
            inline=False
        )
        embed.add_field(
            name='Note',
            value=('If you are an admin looking to configure your server, try '
                   f'`{ctx.prefix}admin` for instructions to get started.')
        )

        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Self(bot))
