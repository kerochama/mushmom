"""
Help commands

"""
from __future__ import annotations  # forward reference

import discord
import itertools

from discord.ext import commands
from discord import app_commands

from typing import Optional, Mapping, List, Sequence, Any

from .. import config
from ..resources import EMOJIS, ATTACHMENTS
from .utils.parameters import contains
from .utils.checks import slash_in_guild_channel

HELP_PAGES = ['Get Started', 'Demo', 'Admin', 'Invite Bot', 'Support']


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @slash_in_guild_channel()
    @app_commands.autocomplete(topic=contains(HELP_PAGES))
    async def help(
            self,
            interaction: discord.Interaction,
            topic: Optional[str] = None
    ) -> None:
        """
        Info about the bot divided by topic

        Parameters
        ----------
        interaction: discord.Interaction
        topic: Optional[str]
            the topic you want to learn about

        """
        args = {}

        if not topic:
            args['embed'] = self._about_embed()
        elif topic == 'Get Started':
            args['content'] = ATTACHMENTS['get_started'].url
        elif topic == 'Demo':
            args['content'] = config.urls.demo
        elif topic == 'Admin':
            args['embed'] = self._admin_embed()
        elif topic == 'Support':
            args['content'] = config.urls.invite
        elif topic == 'Invite Bot':
            args['embed'] = self._add_bot_embed()

        await interaction.response.send_message(**args)

    def _about_embed(self) -> discord.Embed:
        embed = discord.Embed(
            description=(f'{config.core.bot_name} is a bot that will send '
                         'emotes and actions for you. For a in-depth '
                         'explanations, demos, and more, visit the '
                         f'[{config.core.bot_name}]({config.urls.website}) '
                         'website.\n\u200b\nTopics available in `/help` '
                         'include:\n\u200b'),
            color=config.core.embed_color
        )

        embed.add_field(
            name='Get Started',
            value='Instructions for importing your character\n\u200b',
        )
        embed.add_field(
            name='Demo',
            value='A demo of some of the commands available\n\u200b',
        )
        embed.add_field(
            name='Admin',
            value=('Instructions for admins to configure server settings'
                   '\n\u200b'),
        )
        embed.add_field(
            name='Invite Bot',
            value=(f'[Add {config.core.bot_name}]({config.urls.add_bot}) '
                   'to your server\n\u200b'),
        )
        embed.add_field(
            name='Support',
            value=(f'Join us on the {config.core.bot_name} [server]' 
                   f'({config.urls.invite})\n\u200b'),
        )
        embed.add_field(
            name='\u200b',
            value='\u200b',
        )

        embed.set_author(name=f'About {config.core.bot_name}',
                         icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji(EMOJIS['mushparty'].id).url
        embed.set_thumbnail(url=thumbnail)
        embed.set_image(url=ATTACHMENTS['mushmomheader'].url)

        return embed

    def _admin_embed(self) -> discord.Embed:
        """Instructions for admins to set up server"""
        embed = discord.Embed(
            description=('Admins have a number of configuration commands that '
                         f'can be used to customize {config.core.bot_name} to '
                         'your server. A few common settings or issues are '
                         'highlighted below:\n\u200b'),
            color=config.core.embed_color
        )

        embed.set_author(name=f'{config.core.bot_name} Admin',
                         icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji(EMOJIS['mushcheers'].id).url
        embed.set_thumbnail(url=thumbnail)

        embed.add_field(
            name='Bot Channel',
            value=('```Restrict commands to a specific channel by using the '
                   f'command `@{config.core.bot_name} set channel` in the '
                   'desired channel or supplying the channel at the end of '
                   'the command. Emotes, poses, and actions can still be used '
                   'everywhere.```\u200b'),
            inline=False
        )
        embed.add_field(
            name='Emotes Command Deletion',
            value=('```If your commands are not deleting properly in certain '
                   'channels, make sure the bot has the ability to both '
                   '`Manage Webhooks` and `Manage Messages`.```\u200b'),
            inline=False
        )

        return embed

    def _add_bot_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'Add {config.core.bot_name}',
            description=(f'Click the title to invite {config.core.bot_name} '
                         'to your server. You will be asked to grant it the '
                         'following permissions:\n\u200b'),
            url=config.urls.add_bot,
            color=config.core.embed_color
        )

        permissions = [
            'Manage Emoji and Sticks',
            'Manage Webhooks',
            'Read, Send, & Manage Messages',
            'Embed Links',
            'Attach Files',
            'Read Message History',
            'Mention @everyone, @here, and All Roles',
            'Add Reactions',
            'Use External Emoji',
            'Use Application Commands'
        ]

        delim = '\n\u2727 \u200b '
        embed.add_field(
            name='Permissions',
            value=f'\u2727 \u200b {delim.join(permissions)}\n\u200b'
        )

        embed.set_author(name=f'{config.core.bot_name}',
                         icon_url=self.bot.user.display_avatar.url)
        thumbnail = self.bot.get_emoji(EMOJIS['mushcheers'].id).url
        embed.set_thumbnail(url=thumbnail)
        embed.set_image(url=ATTACHMENTS['mushmomheader'].url)

        return embed


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


async def setup(bot):
    await bot.add_cog(Help(bot))
