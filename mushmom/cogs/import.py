"""
Import character commands

"""
import discord

from discord.ext import commands


class Import(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

