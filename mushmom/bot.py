import discord
import os
import typing
import aiohttp
import inspect

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


@bot.command(name='import', ignore_extra=False)
async def _import(ctx, name: utils.ImportNameConverter,
                  url: typing.Optional[utils.MapleIOURLConverter] = ''):
    # parse char data
    if url:  # maplestory.io char api
        char = Character.from_url(url)
    elif ctx.message.attachments:  # json output of sim and studio
        json_file = next((att for att in ctx.message.attachments
                          if att.filename[-5:] == '.json'), None)

        if not json_file:
            raise errors.UnexpectedFileTypeError

        # get json
        async with aiohttp.ClientSession() as session:
            async with session.get(json_file.url) as r:
                if r.status == 200:
                    data = await r.json()
                else:
                    raise errors.DiscordIOError

        char = Character.from_json(data)
    else:
        # doesnt matter which param.  Handled in error message
        raise commands.MissingRequiredArgument(
            inspect.Parameter('url', inspect.Parameter.POSITIONAL_ONLY)
        )

    char.name = name

    # query database
    user = await db.get_user(ctx.author.id)

    if not user:  # user has no saved chars
        ret = await db.add_user(ctx.author.id, char.to_dict())
    elif len(user['chars']) < config.MAX_CHARS:
        user['chars'].append(char.to_dict())
        ret = await db.set_user(ctx.author.id, {'chars': user['chars']})
    else:
        # handle more than 5 chars
        print('else')
        ret = None

    if ret:
        await ctx.send(f'{name} has been successfully mushed')
    else:
        raise errors.DataWriteError


@_import.error
async def _import_error(ctx, error):
    append_text = ' \u200b Try:\n\u200b'
    cmds = {
        'Commands': '\n'.join([
            '`mush import [name] [url: maplestory.io]`',
            '`mush import [name]` with a JSON file attached'
        ])
    }

    if isinstance(error, commands.TooManyArguments):
        msg = f'{config.BOT_NAME} did not understand.'
    elif isinstance(error, commands.BadArgument):
        msg = 'You must supply a character name to start mushing!'
    elif isinstance(error, commands.MissingRequiredArgument):
        if error.param.name == 'name':
            msg = 'You must supply a character name to start mushing!'
        elif error.param.name == 'url':
            msg = 'Missing source data.'
    elif isinstance(error, errors.UnexpectedFileTypeError):
        msg = f'{config.BOT_NAME} only accepts JSON files'
        append_text = ''
        cmds = None
    elif isinstance(error, errors.DiscordIOError):
        msg = (f'Error trying to read attached JSON file.'
               '\u200b Try again later')
        append_text = ''
        cmds = None
    elif isinstance(error, errors.DataWriteError):
        msg = 'Problem saving character. \u200b Try again later'
        append_text = ''
        cmds = None

    if msg:
        await errors.send(ctx, msg, append=append_text, fields=cmds)


@bot.group(invoke_without_command=True, ignore_extra=False)
async def sprite(ctx,
                 emotion: typing.Optional[utils.EmotionConverter] = 'default',
                 pose: typing.Optional[utils.PoseConverter] = 'stand1'):
    # grab character
    char_data = await db.get_char_data(ctx.author.id)

    if not char_data:
        raise errors.DataNotFound

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
        msg = 'Emotion/pose not found. \u200b See:\n\u200b'
        fields = {
            'Commands': '\n'.join([
                f'`{bot.command_prefix[0]}sprite emotions`',
                f'`{bot.command_prefix[0]}sprite poses`'
            ])
        }
    elif isinstance(error, errors.DataNotFound):
        msg = 'No registered character. \u200b See:\n\u200b'
        fields = {'Commands': f'`{bot.command_prefix[0]}import`'}
    elif isinstance(error, errors.MapleIOError):
        msg = 'Could not get maple data. \u200b Try again later'
        fields = None

    if msg:
        await errors.send(ctx, msg, fields=fields)


@sprite.command()
async def emotions(ctx):
    embed = discord.Embed(
        description=('The following is a list of emotions you can use in the '
                     'generation of your emoji or sprite.'),
        color=config.EMBED_COLOR  # hard coded to match current pfp banner
    )

    embed.set_author(name='Emotions', icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=config.EMOJIS['mushheart'])
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
    embed.set_thumbnail(url=config.EMOJIS['mushdab'])
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

