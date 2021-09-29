"""
Commands to change things about the bot itself

"""
import discord

from discord.ext import commands


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, extension):
        """
        Load an extension dynamically from cogs

        :param ctx:
        :param extension:
        :return:
        """
        self.bot.load_extension(f'cogs.{extension}')
        await ctx.send(f'Loaded `cogs.{extension}`')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, extension):
        """
        Load an extesion dynamically from cogs

        :param ctx:
        :param extension:
        :return:
        """
        self.bot.unload_extension(f'cogs.{extension}')
        await ctx.send(f'Unloaded `cogs.{extension}`')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, extension):
        """
        Load an extesion dynamically from cogs

        :param ctx:
        :param extension:
        :return:
        """
        self.bot.unload_extension(f'cogs.{extension}')
        self.bot.load_extension(f'cogs.{extension}')
        await ctx.send(f'Reloaded`cogs.{extension}`')


def setup(bot):
    bot.add_cog(Meta(bot))
