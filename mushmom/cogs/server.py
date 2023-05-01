"""
Basic commands related to bot

"""
from discord.ext import commands
from typing import Optional

from .. import config
from .utils import errors


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context):
        # only admins can run commands from this cog
        is_admin = commands.has_permissions(administrator=True).predicate
        return await is_admin(ctx)

    @commands.group(hidden=True)
    async def set(self, ctx: commands.Context):
        pass

    @set.command(name='channel')
    async def _set_channel(
            self,
            ctx: commands.Context,
            channel: Optional[commands.TextChannelConverter]
    ) -> None:
        """
        Set channel for non-emote commands (admin only)

        Parameters
        ----------
        ctx: commands.Context
        channel: Optional[commands.TextChannelConverter]
            channel to set. If not specified, use current channel

        """
        guild = await self.bot.db.get_guild(ctx.guild.id)
        data = {'channel': channel.id if channel else ctx.channel.id}

        if not guild:
            ret = await self.bot.db.add_guild(ctx.guild.id, data)
        else:
            ret = await self.bot.db.set_guild(ctx.guild.id, data)

        if ret.acknowledged:
            msg = (f'**{config.core.bot_name}** command channel set '
                   f'to <#{data["channel"]}>')
            await ctx.send(msg)
        else:
            raise errors.DatabaseWriteError

    @commands.group(hidden=True)
    async def reset(self, ctx: commands.Context):
        pass

    @reset.command(name='channel')
    async def _reset_channel(self, ctx: commands.Context) -> None:
        """
        Remove guild channel restrictions (admin only)

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
                raise errors.DatabaseWriteError
        else:
            msg = f'All **{ctx.guild.name}** channels can already be used'
            await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Server(bot))
