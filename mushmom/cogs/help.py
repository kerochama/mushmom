"""
Custom help command

"""
import discord

from typing import Iterable, Union, Optional
from discord.ext import commands
from inspect import isclass

from .. import config
from . import reference
from .utils import converters


def _show_help(
        ctx: commands.Context,
        command: commands.Command,
        show_hidden: bool = False
) -> bool:
    try:
        pass_checks = all(check(ctx) for check in command.checks)
    except commands.CheckFailure:
        return False

    return pass_checks and (not command.hidden or show_hidden)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _qualified_name(
            self,
            command: Union[commands.Command, str],
            alias_of: Optional[commands.Command] = None
    ) -> Optional[str]:
        """
        Format qualified name of command, even if alias given

        Parameters
        ----------
        command: Union[commands.Command, str]
            the command or command name
        alias_of: Optional[commands.Command]
            the aliased command if known

        Returns
        -------
        Optional[str]
            qualified command/alias name or None if not found

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

    def get_cmd_name(
            self,
            ctx: commands.Context,
            command: Union[commands.Command, str],
            alias_of: Optional[commands.Command] = None,
            formatted: bool = True
    ) -> Optional[str]:
        """

        Parameters
        ----------
        ctx: commands.Context
        command: Union[commands.Command, str]
            the command or command name
        alias_of: Optional[commands.Command]
            the aliased command if known
        formatted: bool
            whether or not to wrap in code `s

        Returns
        -------
        Optional[str]
            prefix + command name or None if not found

        """
        name = self._qualified_name(command, alias_of)
        if not name:  # command not found in bot
            return

        full_name = f'{ctx.prefix}{name}'
        return f'`{full_name}`' if formatted else full_name

    def get_signature(
            self,
            command: Union[commands.Command, str],
            alias_of: Optional[commands.Command] = None
    ) -> Optional[list[str]]:
        """
        Get all signatures for command.  If alias passed, return the
        alias signature

        Searches for signatures in cogs.reference.HELP first

        Parameters
        ----------
        command: Union[commands.Command, str]
            the command or command name
        alias_of: Optional[commands.Command]
            the aliased command if known

        Returns
        -------
        Optional[list[str]]
            signatures

        """
        cmd = (alias_of or self.bot.get_command(command)
               if isinstance(command, str) else command)
        if not cmd:  # command not found in bot
            return

        try:
            cog = cmd.cog_name.lower()
            sigs = reference.HELP[cog][cmd.qualified_name]['sigs']
        except KeyError:
            sigs = [cmd.signature]

        return sigs

    def get_usage(
            self,
            ctx: commands.Context,
            command: Union[commands.Command, str],
            alias_of: Optional[commands.Command] = None
    ) -> Optional[list[str]]:
        """
        Full call (command + signature).  If alias passed, return the
        alias signature

        Parameters
        ----------
        ctx: commands.Context
        command: Union[commands.Command, str]
            the command or command name
        alias_of: Optional[commands.Command]
            the aliased command if known

        Returns
        -------
        Optional[list[str]]
            prefix + command + signature or None if not found

        """
        name = self.get_cmd_name(ctx, command, alias_of, formatted=False)
        sigs = self.get_signature(command, alias_of)

        if not name:  # command not found
            return

        return [f'`{name}{" " + sig if sig else sig}`' for sig in sigs]

    def get_options(
            self,
            command: Union[commands.Command, str],
            alias_of: Optional[commands.Command] = None
    ) -> Optional[list[str]]:
        """
        Check annotations for FlagConverter. Return list of flags
        and aliases

        Parameters
        ----------
        command: Union[commands.Command, str]
            the command or command name
        alias_of: Optional[commands.Command]
            the aliased command if known

        Returns
        -------
        Optional[list[str]]
            list of flags. each item will be a csl of name, aliases

        """
        cmd = (alias_of or self.bot.get_command(command)
               if isinstance(command, str) else command)
        if not cmd:  # command not found in bot
            return

        anno_iter = (x for x in cmd.callback.__annotations__.values()
                     if isclass(x) and issubclass(x, commands.FlagConverter))
        _options = next(anno_iter, None)

        # FlagConverter object found
        if _options:
            opts = [[k] + v.aliases for k, v in _options.get_flags().items()]
            fmt = [', '.join([f'`{flag}`' for flag in x]) for x in opts]
            return fmt

    def _prepare_cmds(
            self,
            commands: Iterable[Union[commands.Command, str]],
            aliases: bool = False
    ) -> Iterable[Union[commands.Command, str]]:
        """
        Expand to include alias in aliases=True

        Parameters
        ----------
        commands: Iterable[Union[commands.Command, str]]
            list of commands or command names
        aliases: bool
            whether or not to include aliases

        Returns
        -------
        Iterable[Union[commands.Command, str]]
            the expanded list of commands or command names

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

    def get_all_cmd_names(
            self,
            ctx: commands.Context,
            commands: Iterable[Union[commands.Command, str]],
            aliases: bool = False
    ) -> Iterable[str]:
        """
        Get full command names without parameters

        Parameters
        ----------
        ctx: commands.Context
        commands: Iterable[Union[commands.Command, str]]
            list of commands or command names
        aliases: bool
            whether or not to include aliases

        Returns
        -------
        Iterable[str]
            the expanded list of command names with prefix

        """
        cmds = self._prepare_cmds(commands, aliases=aliases)
        names = list(filter(  # filter out None
            lambda x: x,
            [self.get_cmd_name(ctx, c) for c in cmds]
        ))
        return list(dict.fromkeys(names))  # ordered dict keys = set

    def get_all_usages(
            self,
            ctx: commands.Context,
            commands: Iterable[Union[commands.Command, str]],
            aliases: bool = False
    ) -> Iterable[str]:
        """
        Get command calls for all commands given
        Parameters
        ----------
        ctx: commands.Context
        commands: Iterable[Union[commands.Command, str]]
            list of commands or command names
        aliases: bool
            whether or not to include aliases
        Returns
        -------
        Iterable[str]
            the expanded list of command calls
        """
        cmds = self._prepare_cmds(commands, aliases=aliases)
        usages = list(filter(  # filter out None
            lambda x: x,
            [usage for c in cmds for usage in self.get_usage(ctx, c)]
        ))
        return list(dict.fromkeys(usages))  # ordered dict keys = ordered set

    @commands.command(ignore_extra=False)
    async def help(
            self,
            ctx: commands.Context,
            *,
            command: Optional[converters.CommandConverter] = None
    ) -> discord.Message:
        """
        The command that generated this message

        Parameters
        ----------
        ctx: commands.Context
        command: Optional[str]
            the command for which to get help

        Returns
        -------
        discord.Message
            the help message sent

        """
        if command is None:
            return await self.send_bot_help(ctx)
        else:
            return await self.send_command_help(ctx, command)

    def get_bot_mapping(self) -> dict[str, list[commands.Command]]:
        """
        Get dict of cog_name: [command, ...] of bot

        Returns
        -------
        dict[str, list[commands.Command]]
            a mapping of cog_name to list of commands in cog including
            subcommands

        """
        mapping = {}

        # include subcommands and aliases
        for cmd in self.bot.commands:
            cog_name = cmd.cog_name or 'Other'

            if isinstance(cmd, commands.Group):
                if cmd.invoke_without_command:
                    mapping.setdefault(cog_name, []).append(cmd)

                for subcmd in cmd.walk_commands():
                    mapping.setdefault(cog_name, []).append(subcmd)
            else:  # regular command
                mapping.setdefault(cog_name, []).append(cmd)

        return mapping

    async def send_bot_help(self, ctx: commands.Context) -> discord.Message:
        """
        Creates embed with list of all commands that are callable in bot
        categorized by cog_name and send.  reference.HELP is checked and commands
        are listed even if the underlying command is hidden so long as it
        passes all checks

        Parameters
        ----------
        ctx: commands.Context

        Returns
        -------
        discord.Message
            the help message sent

        """
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
                         icon_url=self.bot.user.avatar.url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushhuh)
        embed.set_thumbnail(url=thumbnail)

        # add commands as fields by cog
        mapping = self.get_bot_mapping()

        for cog in sorted(mapping):  # in alphabetical order
            cmds = filter(lambda c: _show_help(ctx, c), mapping[cog])
            cmd_names = self.get_all_cmd_names(ctx, cmds, aliases=True)

            try:  # check reference.HELP
                _ref = {k: v for k, v in self.bot.ref_aliases.items()
                        if _show_help(ctx, v, show_hidden=True)}
                _cmds = [self.get_cmd_name(ctx, alias, cmd)
                         for alias, cmd in _ref.items() if cmd.cog_name == cog]
                cmd_names += _cmds
            except KeyError:
                pass

            if cmd_names:  # ordered dict keys = ordered set
                unique = list(dict.fromkeys(cmd_names)) + ['\u200b']
                embed.add_field(name=cog, value='\n'.join(unique))

        return await ctx.send(embed=embed)

    async def send_command_help(
            self,
            ctx: commands.Context,
            command: str
    ) -> discord.Message:
        """
        Create and embed with information about command and send.
        Includes description, usage, options, and aliases

        Parameters
        ----------
        ctx: commands.Context
        command: str
            full qualified command name

        Returns
        -------
        discord.Message
            the help message sent

        """
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
                         icon_url=self.bot.user.avatar.url)
        thumbnail = self.bot.get_emoji_url(config.emojis.mushhuh)
        embed.set_thumbnail(url=thumbnail)

        # show usage
        usage = self.get_usage(ctx, command) + ['\u200b']  # extra white space
        embed.add_field(name='Usage', value='\n'.join(usage), inline=False)

        # show options
        options = self.get_options(cmd)
        if options:
            embed.add_field(name='Options', value='\n'.join(options))

        # show aliases
        if cmd.aliases:
            aliases = self.get_all_cmd_names(ctx, [command], aliases=True)
            aliases.remove(f'`{ctx.prefix}{command}`')
            embed.add_field(name='Aliases', value='\n'.join(aliases))

        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
