"""
Basic commands related to bot

"""
import discord

from discord.ext import commands


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send('hai')


def setup(bot):
    bot.add_cog(Core(bot))
