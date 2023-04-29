"""
Commands to change things about the bot itself

"""
from discord.ext import commands
from typing import Optional

from .. import config


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context):
        # only owner can run commands from this cog
        return await self.bot.is_owner(ctx.author)

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

    @commands.command(hidden=True)
    async def sync(self,
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
        n = await self.bot.tree.sync(guild=guild)
        await ctx.send(f'{len(n)} slash commands synced')

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
