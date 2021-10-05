"""
Custom help command

"""
import discord

from typing import Iterable, Union
from discord.ext import commands

from .. import config
from . import ref


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _qualified_name(self, command, alias_of=None):
        """
        Format qualified name of command, even if alias given

        :param command:
        :param alias_of: if known, to resolve leaf alias name given
        :return:
        """
        if isinstance(command, str):
            cmd = alias_of or self.bot.get_command(command)
            if not cmd:  # command not found in bot
                return

            # replace last x tokens
            tokens = command.split(' ')
            _name = cmd.qualified_name.split(' ')
            _name[-len(tokens):] = tokens
            name = ' '.join(_name)
        else:
            name = command.qualified_name

        return name

    def get_cmd_name(self, ctx, command, alias_of=None, formatted=True):
        """
        Get prefixed, qualified command name.  If alias passed return the
        alias name

        :param ctx:
        :param command:
        :param alias_of: if known, to resolve leaf alias name given
        :param formatted: whether to wrap in ``
        :return:
        """
        name = self._qualified_name(command, alias_of)
        full_name = f'{ctx.prefix}{name}'
        return f'`{full_name}`' if formatted else full_name

    def get_signature(self, command, alias_of=None):
        """
        Get all signatures for command.  If alias passed, return the
        alias signature

        :param command:
        :param alias_of: if known, to resolve leaf alias name given
        :return:
        """
        cmd = (alias_of or self.bot.get_command(command)
               if isinstance(command, str) else command)
        if not cmd:  # command not found in bot
            return

        try:
            cog = cmd.cog_name.lower()
            sigs = ref.HELP[cog][cmd.qualified_name]['sigs']
        except KeyError:
            sigs = [cmd.signature]

        return sigs

    def get_usage(self, ctx, command, alias_of=None):
        """
        Full call (command + signature).  If alias passed, return the
        alias signature

        :param ctx:
        :param command:
        :param alias_of: if known, to resolve leaf alias name given
        :return:
        """
        name = self.get_cmd_name(ctx, command, alias_of, formatted=False)
        sigs = self.get_signature(command, alias_of)

        if not name:  # command not found
            return

        return [f'`{name}{" " + sig if sig else sig}`' for sig in sigs]

    def _prepare_cmds(self, commands, aliases=False):
        """
        Expand to include alias in aliases=True

        :param commands:
        :param aliases:
        :return:
        """
        if aliases:
            cmds = [self.bot.get_command(c) if isinstance(c, str) else c
                    for c in commands]
            cmds = list(filter(lambda x: x, cmds))  # remove invalid cmds
            _expand = [[c] + [self._qualified_name(a, c) for a in c.aliases]
                       for c in cmds]
            cmds = [c for cs in _expand for c in cs]
        else:
            cmds = commands

        return cmds

    def get_cmd_names(self, ctx, commands, aliases=False):
        """
        Get full command names without parameters

        :param ctx:
        :param commands:
        :param aliases:
        :return:
        """
        cmds = self._prepare_cmds(commands, aliases=aliases)
        names = list(filter(  # filter out None
            lambda x: x,
            [self.get_cmd_name(ctx, c) for c in cmds]
        ))
        return list(dict.fromkeys(names))  # ordered dict keys = set

    def get_usages(self, ctx, commands, aliases=False):
        """
        Get full command names without parameters

        :param ctx:
        :param commands:
        :param aliases:
        :return:
        """
        cmds = self._prepare_cmds(commands, aliases=aliases)
        usages = list(filter(  # filter out None
            lambda x: x,
            [usage for c in cmds for usage in self.get_usage(ctx, c)]
        ))
        return list(dict.fromkeys(usages))  # ordered dict keys = set

    @commands.command()
    async def help(self, ctx, *, command=None):
        """
        The command that generated this message

        :param ctx:
        :param command:
        :return:
        """
        if command is None:
            return await self.send_bot_help(ctx)
        else:
            return await self.send_command_help(ctx, command)

    def get_bot_mapping(self, filter=lambda cmd: not cmd.hidden):
        """
        Get dict of cog: [command, ...] of bot

        :param filter:
        :return:
        """
        mapping = {}

        for cmd in self.bot.commands:  # include subcommands and aliases
            if not filter(cmd):  # skip hidden commands by default
                continue

            cog_name = cmd.cog_name or 'Other'

            if isinstance(cmd, commands.Group):
                if cmd.invoke_without_command:
                    mapping.setdefault(cog_name, []).append(cmd)

                for subcmd in cmd.walk_commands():
                    mapping.setdefault(cog_name, []).append(subcmd)
            else:  # regular command
                mapping.setdefault(cog_name, []).append(cmd)

        return mapping

    async def send_bot_help(self, ctx):
        embed = discord.Embed(
            description=(f'{config.core.bot_name} will send emotes and '
                         'actions for you. To get started, check out '
                         f'`{ctx.prefix}import`. Type `{ctx.prefix}help '
                         '<command>` for more information on a command.\n\n'
                         f'`{ctx.prefix}[args]` without a command will call '
                         f'`{ctx.prefix}emote [args]`\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name=f'{config.core.bot_name} Help',
                         icon_url=self.bot.user.avatar_url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushheart)
        embed.set_thumbnail(url=thumbnail)

        # add commands as fields by cog
        mapping = self.get_bot_mapping()

        for cog in sorted(mapping.keys()):  # in alphabetical order
            cmd_names = self.get_cmd_names(ctx, mapping[cog], aliases=True)
            embed.add_field(name=cog, value='\n'.join(cmd_names))

        return await ctx.send(embed=embed)

    async def send_command_help(self, ctx, command):
        # check if exists
        cmd = self.bot.get_command(command)

        if not cmd:  # not a command
            return

        # clean help
        cmd_help = (cmd.help
                    .split('\n\n')[0]  # before first empty line
                    .replace('\n', ' ')  # handle line breaks
                    .format(prefix=ctx.prefix))

        embed = discord.Embed(
            title=f'{ctx.prefix}{command}',
            description=f'{cmd_help}\n\u200b',
            color=config.core.embed_color
        )

        embed.set_author(name=f'Command Help',
                         icon_url=self.bot.user.avatar_url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushheart)
        embed.set_thumbnail(url=thumbnail)

        # show usage
        usage = self.get_usage(ctx, command) + ['\u200b']  # extra white space
        embed.add_field(name='Usage', value='\n'.join(usage), inline=False)

        # show options
        try:
            cog = cmd.cog_name.lower()
            _options = ref.HELP[cog][cmd.qualified_name]['options']
            options = [f'`{option}`' for option in _options]
            embed.add_field(name='Options', value='\n'.join(options))
        except KeyError:
            pass

        if cmd.aliases:
            aliases = self.get_cmd_names(ctx, [command], aliases=True)
            aliases.remove(f'`{ctx.prefix}{command}`')
            embed.add_field(name='Aliases', value='\n'.join(aliases))

        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
