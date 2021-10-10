"""
Basic commands related to bot

"""
import discord

from discord.ext import commands

from .. import config
from ..utils import errors


class Server(commands.Cog):
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
    async def prefixes(self, ctx: commands.Context) -> None:
        """
        Send the current list of prefixes

        Parameters
        ----------
        ctx: commands.Context

        """
        _prefixes = await self.bot.command_prefix(self.bot, ctx.message)
        prefixes = [f'`{prefix}`' for prefix in _prefixes]

        embed = discord.Embed(description='\n'.join(prefixes),
                              color=config.core.embed_color)
        embed.set_author(name='Prefixes', icon_url=self.bot.user.avatar.url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushparty)
        embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)

    @commands.command()
    async def channel(self, ctx: commands.Context) -> None:
        """
        Reply with the guild channel set. Commands other than emotes,
        sprites, and actions can only be run here.  If no channel is set,
        command can be run in all channels

        Parameters
        ----------
        ctx: commands.Context

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)

        if guild and guild['channel']:
            msg = (f'The designated **{config.core.bot_name}** command channel'
                   f' is <#{guild["channel"]}>')
        else:
            msg = (f'**{ctx.guild.name}** has no designated '
                   f'**{config.core.bot_name}** command channel')

        await ctx.send(msg)

    @commands.command(name='set', hidden=True)
    @commands.has_permissions(administrator=True)
    async def _set(self, ctx: commands.Context, setting: str, *args) -> None:
        """
        Sets specified guild setting

        Parameters
        ----------
        ctx: commands.Context
        setting: str
            the setting to set

        Notes
        -----
        This command manually acts like a group since 'set prefixes'
        would name clash with the 'prefixes' command.  Help still
        functions as if this were a group call by directly aliasing the
        hidden commands in help.yaml

        """
        if setting == 'prefixes':
            await self._set_prefixes(ctx, *args)
        elif setting == 'channel':
            await self._set_channel(ctx)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def _set_prefixes(
            self,
            ctx: commands.Context,
            *prefixes
    ) -> None:
        """
        Set guild prefixes. **Admin only**

        Parameters
        ----------
        ctx: commands.Context
        prefixes: list[str]
            list of prefixes to add

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)
        data = {'prefixes': prefixes}

        if not guild:
            ret = await self.bot.db.add_guild(ctx.guild.id, data)
        else:
            ret = await self.bot.db.set_guild(ctx.guild.id, data)

        if ret.acknowledged:
            _prefixes = await self.bot.command_prefix(self.bot, ctx.message)
            prefixes = [f'`{prefix}`' for prefix in _prefixes]
            await ctx.send(f'Prefixes were set to: {", ".join(prefixes)}')
        else:
            raise errors.DataWriteError

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def _set_channel(self, ctx: commands.Context) -> None:
        """
        Set designated command channel. Emote, sprite, and action
        commands can run anywhere. **Admin only**

        Parameters
        ----------
        ctx: ctx.commands.Context

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)
        data = {'channel': ctx.channel.id}

        if not guild:
            ret = await self.bot.db.add_guild(ctx.guild.id, data)
        else:
            ret = await self.bot.db.set_guild(ctx.guild.id, data)

        if ret.acknowledged:
            msg = (f'**{config.core.bot_name}** command channel set '
                   f'to <#{ctx.channel.id}>')
            await ctx.send(msg)
        else:
            raise errors.DataWriteError

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx: commands.Context, setting: str) -> None:
        """
        Sets specified guild setting to default value

        Parameters
        ----------
        ctx: commands.Context
        setting: str
            the setting to set

        Notes
        -----
        This command manually acts like a group since 'set prefixes'
        would name clash with the 'prefixes' command.  Help still
        functions as if this were a group call by directly aliasing the
        hidden commands in help.yaml

        """
        if setting == 'prefixes':
            await self._reset_prefixes(ctx)
        elif setting == 'channel':
            await self._reset_channel(ctx)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def _reset_prefixes(self, ctx: commands.Context) -> None:
        """
        Set guild prefixes to default. **Admin only**

        Parameters
        ----------
        ctx: commands.Context

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)
        default = {'prefixes': []}

        if guild:
            ret = await self.bot.db.set_guild(ctx.guild.id, default)
            if ret.acknowledged:
                msg = f'Prefixes were set to: `{config.core.default_prefix}`'
                await ctx.send(msg)
            else:
                raise errors.DataWriteError
        else:
            msg = f'**{ctx.guild.name}** already uses default prefixes'
            await ctx.send(msg)

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def _reset_channel(self, ctx: commands.Context) -> None:
        """
        Set guild channel to default (all channels). **Admin only**

        Parameters
        ----------
        ctx: commands.Context

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)
        default = {'channel': None}

        if guild:
            ret = await self.bot.db.set_guild(ctx.guild.id, default)
            if ret.acknowledged:
                msg = 'All channels can now be used for **{}** commands'
                await ctx.send(msg.format(config.core.bot_name))
            else:
                raise errors.DataWriteError
        else:
            msg = f'All **{ctx.guild.name}** channels can already be used'
            await ctx.send(msg)


def setup(bot):
    bot.add_cog(Server(bot))
