"""
Custom help command

"""
from typing import Iterable, Union
from discord.ext import commands

from . import ref


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_command_base(self, ctx, cmd):
        prefix = self.bot.command_prefix(self.bot, ctx.message)[0]
        return f'`{prefix}{cmd.qualified_name}'

    def get_signature(self, ctx, cmd, aliases=False):
        """
        Build full signature

        :param ctx:
        :param cmd:
        :return:
        """
        prefix = ''
        return (f'`{prefix}{cmd.qualified_name}'
                f'{" " + cmd.signature if cmd.signature else ""}`')

    def get_signatures(self, ctx,
                       cmds: (Iterable[Union[commands.Command, str]])):
        """
        Get all signatures from command list

        :param ctx:
        :param cmds:
        :return: list of signatures
        """
        if cmds and isinstance(cmds[0], str):
            cmds = list(filter(lambda x: x,  # throw away not found
                               [self.bot.get_command(c) for c in cmds]))
        return [self.get_signature(ctx, c) for c in cmds]


def setup(bot):
    bot.add_cog(Help(bot))
