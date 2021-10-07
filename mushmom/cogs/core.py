"""
Basic commands related to bot

"""
import discord

from discord.ext import commands


class Core(commands.Cog):
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


def setup(bot):
    bot.add_cog(Core(bot))
