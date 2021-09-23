import discord
import os
import typing

from discord.ext import commands
from io import BytesIO
from dotenv import load_dotenv

from mushmom import config, errors, webhook, utils
from mushmom import database as db
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character

load_dotenv()  # use env variables from .env

bot = commands.Bot(command_prefix=['mush ', '!m '])


@bot.event
async def on_ready():
    print('{0.user} is ready to mush!'.format(bot))


@bot.check
async def valid(ctx):
    """
    Conditions under which bot process message

    :param ctx:
    :return:
    """
    message = ctx.message

    checks = (
        message.author == bot.user,  # ignore self
        message.author.bot  # ignore other bots
    )

    return not any(checks)


@bot.event
async def on_message(message):
    ctx = await bot.get_context(message)

    # ignore message based on checks
    if not await valid(ctx):
        return

    parser = utils.MessageParser(message)

    if parser.has_prefix(bot.command_prefix):
        cmd, args = parser.parse(bot.command_prefix)

        if cmd not in [c.name for c in bot.commands]:  # also fails if None
            if cmd in states.EMOTIONS:
                await _emote(ctx, cmd, args)
        else:
            await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    await ctx.send('hai')


@bot.group(invoke_without_command=True, ignore_extra=False)
async def sprite(ctx,
                 emotion: typing.Optional[utils.EmotionConverter] = 'default',
                 pose: typing.Optional[utils.PoseConverter] = 'stand1'):
    # grab character
    char_data = await db.get_char_data(ctx.author.id)

    if not char_data:
        raise errors.DataNotFoundError

    char = Character.from_json(char_data)
    name = char.name or "char"

    # create sprite
    data = await api.get_sprite(char, pose=pose, emotion=emotion)

    if data:
        if not config.DEBUG:
            await ctx.message.delete()  # delete original message

        img = discord.File(fp=BytesIO(data),
                           filename=f'{name}_{emotion}_{pose}.png')
        await webhook.send_as_author(ctx, file=img)
    else:
        raise errors.MapleIOError


@sprite.error
async def sprite_error(ctx, error):
    if isinstance(error, commands.TooManyArguments):
        await errors.send_error(ctx, f'Emotion/pose not found. \u200b See:'
                                f'\n\n- `{bot.command_prefix[0]}sprite emotions`'
                                f'\n- `{bot.command_prefix[0]}sprite poses`',
                                delete_message=not config.DEBUG)
    elif isinstance(error, errors.DataNotFoundError):
        await errors.send_error(ctx, 'No registered character. \u200b '
                                f'See:\n -`{bot.command_prefix[0]}import`',
                                delete_message=not config.DEBUG)
    elif isinstance(error, errors.MapleIOError):
        await errors.send_error(ctx, 'Could not get maple data. \u200b '
                                'Try again later',
                                delete_message=not config.DEBUG)


@sprite.command()
async def emotions(ctx):
    embed = discord.Embed(
        description=('The following is a list of emotions you can use in the '
                     'generation of your emoji or sprite.'),
        color=config.EMBED_COLOR  # hard coded to match current pfp banner
    )

    embed.set_author(name='Emotions', icon_url=bot.user.avatar_url)
    # embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_footer(text='[GMS v225]')

    # split emotions into 3 lists
    emotions = [states.EMOTIONS[i::3] for i in range(3)]  # order not preserved
    embed.add_field(name='Emotions', value='\n'.join(emotions[0]))
    embed.add_field(name='\u200b', value='\n'.join(emotions[1]))
    embed.add_field(name='\u200b', value='\n'.join(emotions[2]))

    await ctx.send(embed=embed)


@sprite.command()
async def poses(ctx):
    embed = discord.Embed(
        description=('The following is a list of poses you can use in the '
                     'generation of your emoji or sprite.'),
        color=config.EMBED_COLOR  # hard coded to match current pfp banner
    )

    embed.set_author(name='Poses', icon_url=bot.user.avatar_url)
    # embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_footer(text='[GMS v225]')
    embed.add_field(name='Pose', value='\n'.join(states.POSES.keys()))
    embed.add_field(name='Value', value='\n'.join(states.POSES.values()))

    await ctx.send(embed=embed)


# on_message emote commands
async def _emote(ctx, cmd, args=None):
    """
    Handle emote commands (see emotions.json)

    :param ctx:
    :param args:
    :return:
    """
    char = Character.from_json(await db.get_char_data(ctx.author.id))
    name = char.name or "char"

    # create emote
    data = await api.get_emote(char, emotion=cmd)

    if data:
        if not config.DEBUG:
            await ctx.message.delete()  # delete original message

        img = discord.File(fp=BytesIO(data), filename=f'{name}_{cmd}.png')
        await webhook.send_as_author(ctx, file=img)


bot.run(os.getenv('TOKEN'))

