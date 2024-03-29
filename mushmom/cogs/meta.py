"""
Commands to change things about the bot itself

"""
import discord

from discord.ext import commands
from typing import Optional, Union

from .. import config


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context):
        # only owner can run commands from this cog
        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def hello(self, ctx: commands.Context) -> None:
        """
        Say hello to test that the bot is alive

        Parameters
        ----------
        ctx: commands.Context

        """
        await ctx.send('hai')

    @commands.command(hidden=True)
    async def load(self, ctx: commands.Context, extension: str) -> None:
        """
        Load an extension dynamically from cogs

        Parameters
        ----------
        ctx: commands.Context
        extension: str
            extension name (filename without .py)

        """
        await self.bot.load_extension(f'{__package__}.{extension}')
        await ctx.send(f'Loaded `cogs.{extension}`')

    @commands.command(hidden=True)
    async def unload(self, ctx: commands.Context, extension: str) -> None:
        """
        Unload an extension dynamically from cogs

        Parameters
        ----------
        ctx: commands.Context
        extension: str
            extension name (filename without .py)

        """
        await self.bot.unload_extension(f'{__package__}.{extension}')
        await ctx.send(f'Unloaded `cogs.{extension}`')

    @commands.command(hidden=True)
    async def reload(self, ctx: commands.Context, extension: str) -> None:
        """
        Reload an extension dynamically from cogs

        Parameters
        ----------
        ctx: commands.Context
        extension: str
            extension name (filename without .py)

        """
        await self.bot.reload_extension(f'{__package__}.{extension}')
        await ctx.send(f'Reloaded `cogs.{extension}`')

    async def _sync(
            self,
            guild: Union[int, discord.Guild, None] = None
    ) -> str:
        """
        Sync to to guild or globally

        Parameters
        ----------
        guild_id: Optional[int]
            the guild to sync to or None if global

        Returns
        -------
        str
            a message of what was done

        """
        if isinstance(guild, int):
            guild = (self.bot.get_guild(guild)
                     or await self.bot.fetch_guild(guild))
            if not guild:
                return 'Guild not found. 0 commands synced'

        if guild:
            self.bot.tree.copy_global_to(guild=guild)
            n = await self.bot.tree.sync(guild=guild)
            msg = f'Copied {len(n)} global commands to guild'
        else:
            n = await self.bot.tree.sync()
            msg = f'{len(n)} slash commands synced globally'

        return msg

    @commands.command(hidden=True)
    async def sync(
            self,
            ctx: commands.Context,
            sync_level: Optional[str] = None
    ) -> None:
        """
        Sync slash command tree

        Parameters
        ----------
        ctx: commands.Context
        sync_level: Optional[str]
            None or 'all'

        """
        guild = None if sync_level == 'all' else ctx.guild
        msg = await self._sync(guild)
        await ctx.send(msg)

    @commands.command(hidden=True)
    async def quit(self, ctx: commands.Context) -> None:
        """
        Turn off bot from command

        Parameters
        ----------
        ctx: commands.Context

        """
        name = config.core.bot_name
        await ctx.message.reply(f'\u2620 {name} has been killed! \u2620')
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Meta(bot))
