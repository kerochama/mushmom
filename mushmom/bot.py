import discord
import os

from discord.ext import commands
from io import BytesIO
from dotenv import load_dotenv

from mushmom import webhook
from mushmom import database as db, utils
from mushmom.mapleio import api, states
from mushmom.mapleio.character import Character

load_dotenv()  # use env variables from .env

bot = commands.Bot(command_prefix=['mush ', '!m '])


@bot.event
async def on_ready():
    print('{0.user} is ready to mush!'.format(bot))


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
@commands.check(valid)
async def hello(ctx):
    await ctx.send('hai')


@bot.command()
@commands.check(valid)
async def test(ctx):
    print(ctx.message.content)
    print(ctx.message.author)
    print(ctx.message.author.id)


@bot.command()
@commands.check(valid)
async def sprite(ctx, *args):
    cmd = args[0]
    char = Character.from_json(await db.get_char_data(ctx.author.id))
    name = char.name or "char"

    # create sprite
    data = await api.get_sprite(char, emotion=cmd)
    img = discord.File(fp=BytesIO(data), filename=f'{name}_{cmd}.png')
    await webhook.send_as_author(ctx, file=img)


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
    img = discord.File(fp=BytesIO(data), filename=f'{name}_{cmd}.png')
    await webhook.send_as_author(ctx, file=img)


bot.run(os.getenv('TOKEN'))

