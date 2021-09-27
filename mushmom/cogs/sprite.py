"""
Full sprite related commands

"""
import discord

from discord.ext import commands
from typing import Optional
from io import BytesIO

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import converters, errors, webhook
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character


class Sprite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def sprite(self, ctx,
                     emotion: Optional[converters.EmotionConverter] = 'default',
                     pose: Optional[converters.PoseConverter] = 'stand1'):
        # grab character
        char_data = await db.get_char_data(ctx.author.id)

        if not char_data:
            raise errors.DataNotFound

        char = Character.from_json(char_data)
        name = char.name or "char"

        # create sprite
        data = await api.get_sprite(char, pose=pose, emotion=emotion,
                                    session=self.bot.session)

        if data:
            if not config.DEBUG:
                await ctx.message.delete()  # delete original message

            img = discord.File(fp=BytesIO(data),
                               filename=f'{name}_{emotion}_{pose}.png')
            await webhook.send_as_author(ctx, file=img)
        else:
            raise errors.MapleIOError

    @sprite.error
    async def sprite_error(self, ctx, error):
        msg = None
        cmds = None

        if isinstance(error, commands.TooManyArguments):
            msg = 'Emotion/pose not found. \u200b See:\n\u200b'
            cmds = {'Commands': '\n'.join([
                    f'`mush sprite emotions`',
                    f'`mush sprite poses`'
            ])}
        elif isinstance(error, errors.DataNotFound):
            msg = (f'No registered characters. \u200b To import '
                   ' one use:\n\u200b')
            cmds = {'Commands': '\n'.join([
                '`mush add [name] [url: maplestory.io]`',
                '`mush add [name]` with a JSON file attached',
                '`mush import [name] [url: maplestory.io]`',
                '`mush import [name]` with a JSON file attached',
            ])}
        elif isinstance(error, errors.MapleIOError):
            msg = 'Could not get maple data. \u200b Try again later'

        await errors.send(ctx, msg, fields=cmds)

        if msg is None:
            raise error

    @sprite.command()
    async def emotions(self, ctx):
        embed = discord.Embed(
            description=('The following is a list of emotions you can use in the '
                         'generation of your emoji or sprite.\n\u200b'),
            color=config.EMBED_COLOR
        )

        embed.set_author(name='Emotions', icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=config.EMOJIS['mushheart'])
        embed.set_footer(text='[GMS v225]')

        # split emotions into 3 lists
        emotions = [states.EMOTIONS[i::3] for i in range(3)]  # order not preserved
        embed.add_field(name='Emotions', value='\n'.join(emotions[0]))
        embed.add_field(name='\u200b', value='\n'.join(emotions[1]))
        embed.add_field(name='\u200b', value='\n'.join(emotions[2]))

        await ctx.send(embed=embed)

    @sprite.command()
    async def poses(self, ctx):
        embed = discord.Embed(
            description=('The following is a list of poses you can use in the '
                         'generation of your emoji or sprite.\n\u200b'),
            color=config.EMBED_COLOR
        )

        embed.set_author(name='Poses', icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=config.EMOJIS['mushdab'])
        embed.set_footer(text='[GMS v225]')
        embed.add_field(name='Pose', value='\n'.join(states.POSES.keys()))
        embed.add_field(name='Value', value='\n'.join(states.POSES.values()))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Sprite(bot))