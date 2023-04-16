"""
Commands to change things about the bot itself

"""
import discord

from discord.ext import commands
from discord import app_commands
from typing import Optional

from .. import config
from .utils import errors


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

    @commands.group(hidden=True)
    async def timer(self, ctx: commands.Context) -> None:
        pass

    @timer.command(hidden=True)
    async def activate(self, ctx: commands.Context) -> None:
        """Activate timer"""
        ctx.bot.timer.activate()
        await ctx.send('Timer activated')

    @timer.command(hidden=True)
    async def deactivate(self, ctx: commands.Context) -> None:
        """Deactivate timer"""
        ctx.bot.timer.deactivate()
        await ctx.send('Timer deactivated')

    @app_commands.command(name="whoami", description="whoami")
    async def whoami(self, interaction: discord.Interaction):
        raise errors.MushError('blah', see_also=['a'])
        await self.bot.ephemeral(interaction, interaction.user.name)


async def setup(bot):
    await bot.add_cog(Meta(bot))
