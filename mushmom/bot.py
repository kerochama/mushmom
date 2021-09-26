import discord
import os
import aiohttp
import inspect

from discord.ext import commands
from io import BytesIO
from dotenv import load_dotenv
from typing import Optional

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import checks, errors, webhook, converters, io
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character

load_dotenv()  # use env variables from .env


class Core(commands.Cog):
    def __init__(self, bot):
        """
        Basic core commands

        :param bot:
        """
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send('hai')


class Mushmom(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # attach some default commands
        self.add_cog(Core(self))

    async def on_ready(self):
        print(f'{self.user} is ready to mush!')

    async def on_message(self, message):
        """
        Call emotes if no command and emote names are passed

        :param message:
        :return:
        """
        ctx = await self.get_context(message)

        # not handled by other commands
        if (ctx.prefix and not ctx.command
                and all([await check(ctx) for check in self._checks])):
            args = message.content[len(ctx.prefix):].split(' ')
            cmd = args.pop(0)

            if cmd in states.EMOTIONS:  # manually call as emote command
                emotes_cog = self.get_cog('Emotes')

                if emotes_cog:  # emote cog exists
                    if args:  # handle TooManyArguments manually
                        error = commands.TooManyArguments()
                        await emotes_cog.emote_error(ctx, error)
                    else:
                        try:
                            await emotes_cog.emote(ctx, cmd)
                        except commands.CommandError as e:
                            await emotes_cog.emote_error(ctx, e)
        else:
            await self.process_commands(message)


def setup_bot():
    bot = Mushmom(command_prefix=['mush ', '!m '])
    bot.add_check(checks.not_bot)
    bot.load_extension('cogs.emotes')
    bot.load_extension('cogs.characters')

    return bot


bot = setup_bot()


@bot.command(name='import', ignore_extra=False)
async def _import(ctx, name: converters.ImportNameConverter,
                  url: Optional[converters.MapleIOURLConverter] = ''):
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
        prompt = (f'{config.BOT_NAME} can only save {config.MAX_CHARS} '
                  f'character{"s" if config.MAX_CHARS>1 else ""}. \u200b'
                  'Choose a character to replace.')
        sel = await io.select_char(ctx, prompt, user)

        if sel == 'x':
            await ctx.send(f'{name} was not saved')
            ret = None
        else:
            user['chars'][int(sel)-1] = char.to_dict()
            ret = await db.set_user(ctx.author.id, {'chars': user['chars']})

    if ret:
        if ret.acknowledged:
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
    else:
        append_text = ''
        cmds = None

        if isinstance(error, errors.UnexpectedFileTypeError):
            msg = f'{config.BOT_NAME} only accepts JSON files'
        elif isinstance(error, errors.TimeoutError):
            msg = 'No character was selected'
        elif isinstance(error, errors.DiscordIOError):
            msg = (f'Error trying to read attached JSON file.'
                   '\u200b Try again later')
        elif isinstance(error, errors.DataWriteError):
            msg = 'Problem saving character. \u200b Try again later'

            # only handled error that occurs after issuing a prompt
            prompt = await io.get_orphaned_prompt(ctx)
            await prompt.delete()
        else:
            msg = str(error)

    if msg:
        await errors.send(ctx, msg, append=append_text, fields=cmds)


@bot.group(invoke_without_command=True, ignore_extra=False)
async def sprite(ctx,
                 emotion: Optional[converters.EmotionConverter] = 'default',
                 pose: Optional[converters.PoseConverter] = 'stand1'):
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
        color=config.EMBED_COLOR
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
        color=config.EMBED_COLOR
    )

    embed.set_author(name='Poses', icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=config.EMOJIS['mushdab'])
    embed.set_footer(text='[GMS v225]')
    embed.add_field(name='Pose', value='\n'.join(states.POSES.keys()))
    embed.add_field(name='Value', value='\n'.join(states.POSES.values()))

    await ctx.send(embed=embed)


@bot.group()
async def emotes(ctx):
    pass


@emotes.command(name='list')
async def _list(ctx):
    embed = discord.Embed(
        description='The following is a list of emotes you can use\n\u200b',
        color=config.EMBED_COLOR
    )

    embed.set_author(name='Emotes', icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=config.EMOJIS['mushheart'])

    # split emotions into 3 lists
    emotes = [states.EMOTIONS[i::3] for i in range(3)]  # order not preserved
    embed.add_field(name='Emotes', value='\n'.join(emotes[0]))
    embed.add_field(name='\u200b', value='\n'.join(emotes[1]))
    embed.add_field(name='\u200b', value='\n'.join(emotes[2]))

    await ctx.send(embed=embed)


if __name__ == "__main__":
    # bot = setup_bot()
    bot.run(os.getenv('TOKEN'))
