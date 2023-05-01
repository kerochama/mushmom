"""
Help commands

"""
from __future__ import annotations  # forward reference

import discord
import itertools

from discord.ext import commands
from typing import Optional, Mapping, List, Sequence, Any


class FullHelpCommand(commands.DefaultHelpCommand):
    """
    Replace commands with walk_commands and name with qualified_name

    """
    async def send_bot_help(
            self,
            mapping: Mapping[Optional[commands.Cog],
                             List[commands.Command[Any, ..., Any]]],
            /
    ) -> None:
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=True)

        no_category = f'\u200b{self.no_category}:'

        def get_category(command: commands.Command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name + ':' if cog is not None else no_category

        filtered = await self.filter_commands(
            [c for c in bot.walk_commands()], sort=True, key=get_category
        )
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = (sorted(commands, key=lambda c: c.name)
                        if self.sort_commands else list(commands))
            self.add_indented_commands(commands, heading=category, max_size=max_size)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    def add_indented_commands(
            self,
            commands: Sequence[commands.Command[Any, ..., Any]],
            /,
            *,
            heading: str, max_size: Optional[int] = None
    ) -> None:
        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        get_width = discord.utils._string_width
        for command in commands:
            name = command.qualified_name
            width = max_size - (get_width(name) - len(name))
            entry = f'{self.indent * " "}{name:<{width}} {command.short_doc}'
            self.paginator.add_line(self.shorten_text(entry))
