"""
Discord input/output

"""
import discord
import asyncio

from mushmom import config
from mushmom.utils import database as db
from mushmom.utils import errors


async def list_chars(ctx, text, thumbnail=None, user=None):
    """
    List users chars. Returns user and prompt

    :param ctx:
    :param text:
    :param thumbnail:
    :param user: db user if already retrieved
    :return:
    """
    embed = discord.Embed(description=text, color=config.EMBED_COLOR)
    embed.set_author(name='Characters', icon_url=ctx.bot.user.avatar_url)

    if not thumbnail:
        thumbnail = config.EMOJIS['mushparty']

    embed.set_thumbnail(url=thumbnail)

    # get user chars
    if not user:
        user = await db.get_user(ctx.author.id)

    char_names = ['-'] * config.MAX_CHARS

    for i, char in enumerate(user['chars']):
        template = '**{} (default)**' if i == user['default'] else '{}'
        char_names[i] = template.format(char['name'])

    # full width numbers
    char_list = [f'{chr(65297+i)} \u200b {name}' for i, name in enumerate(char_names)]

    embed.add_field(name='Characters', value='\n'.join(char_list))
    msg = await ctx.send(embed=embed)

    return user, msg


async def select_char(ctx, text, user=None):
    """
    Sends embed with list of chars.  User should react to select

    :param ctx:
    :param text:
    :param user: db user if already retrieved
    :return:
    """
    msg = text + ('React to select a character or select \u200b \u274e'
                  ' \u200b to cancel\n\u200b')
    user, prompt = await list_chars(ctx, msg, config.EMOJIS['mushping'], user)

    # numbered unicode emojis 1 - # max chars
    reactions = {f'{x+1}': f'{x+1}\ufe0f\u20e3'
                 for x in range(min(len(user['chars']), config.MAX_CHARS))}
    reactions['x'] = '\u274e'

    # add reactions
    for reaction in reactions.values():
        await prompt.add_reaction(reaction)

    try:
        reaction, user = (
            await ctx.bot.wait_for('reaction_add',
                                   check=(lambda r, u:
                                          u == ctx.author
                                          and r.message.id == prompt.id
                                          and r.emoji in reactions.values()),
                                   timeout=config.DEFAULT_DELAY)
        )
    except asyncio.TimeoutError:
        if not config.DEBUG:
            await prompt.delete()  # clean up prompt

        raise errors.TimeoutError  # handle in command errors

    return next(k for k, v in reactions.items() if reaction.emoji == v)


async def get_orphaned_prompt(ctx):
    """
    Used to grab orphaned prompts that may need to be cleaned

    :param ctx:
    :return:
    """
    # search first 10 messages after ctx.message
    params = {'limit': 10, 'after': ctx.message.created_at}

    async for message in ctx.channel.history(**params):
        # assume prompt
        if (message.author == ctx.bot.user and message.embeds
                and message.embeds[0].author.name == 'Characters'):
            users = set()

            for reaction in message.reactions:
                async for user in reaction.users():
                    users.add(user)

            if ctx.author in users:
                return message
