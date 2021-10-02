"""
Custom help command

"""
from typing import Iterable, Union
from discord.ext import commands

from . import ref


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def main_prefix(self, ctx):
        # first prefix
        return self.bot.command_prefix(self.bot, ctx.message)[0]

    def get_signatures(self, ctx, cmds, aliases=False):
        """
        Build full signatures

        :param ctx:
        :param cmds:
        :param aliases:
        :return:
        """
        if isinstance(cmds, str):
            cmds = [self.bot.get_command(cmds)]
        elif isinstance(cmds, commands.Command):
            cmds = [cmds]
        elif all(isinstance(c, str) for c in cmds):
            cmds = [self.bot.get_command(c) for c in cmds]

        prefix = self.main_prefix(ctx)
        cmds = list(filter(lambda x: x, cmds))
        sigs = []

        for cmd in cmds:
            try:
                cog = cmd.cog.qualified_name.lower()
                _sigs = ref.HELP[cog][cmd.qualified_name]['sigs']
            except KeyError:
                _sigs = [cmd.signature]

            _cmds = [cmd.qualified_name]

            if aliases:
                _cmds += [' '.join(_cmds[0].split(' ')[:-1] + [alias])
                          for alias in cmd.aliases]

            sigs += [f'{prefix}{c}{" " + sig if sig else ""}'
                     for c in _cmds for sig in _sigs]

        return sigs


def setup(bot):
    bot.add_cog(Help(bot))
