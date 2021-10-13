"""
Various functions for making prompts

"""
import discord

from discord.ext import commands
from typing import Optional

from ... import config
from . import errors


async def list_chars(
        ctx: commands.Context,
        user: dict,
        text: str,
        thumbnail: str = None
) -> discord.Message:
    """
    List users chars

    Parameters
    ----------
    ctx: commands.Context
    user: dict
        user data from database
    text: str
        description displayed in embed
    thumbnail: str
        url to the embed thumbnail

    Returns
    -------
    discord.Message
        the message, if sent

    """
    embed = discord.Embed(description=text, color=config.core.embed_color)
    embed.set_author(name='Characters', icon_url=ctx.bot.user.avatar.url)

    if not thumbnail:
        thumbnail = ctx.bot.get_emoji_url(config.emojis.mushparty)

    embed.set_thumbnail(url=thumbnail)

    # format char names
    char_names = ['-'] * config.core.max_chars

    for i, char in enumerate(user['chars']):
        template = '**{} (default)**' if i == user['default'] else '{}'
        char_names[i] = template.format(char['name'])

    # full width numbers
    char_list = [f'{chr(65297 + i)} \u200b {name}'
                 for i, name in enumerate(char_names)]

    embed.add_field(name='Characters', value='\n'.join(char_list))
    msg = await ctx.send(embed=embed)

    return msg


async def get_char(
        ctx: commands.Context,
        user: dict,
        name: Optional[str] = None,
        text: Optional[str] = None
) -> Optional[int]:
    """
    Gets char index if name passed. Otherwise, sends embed with
    list of chars. User should react to select

    Parameters
    ----------
    ctx: commands.Context
    user: dict
        user data from database
    name: str
        the character to be found
    text:
        description displayed in embed prior to instructions

    Returns
    -------
    Optional[int]
        character index or None if cancelled

    """
    if name:
        chars = user['chars']
        char_iter = (i for i, x in enumerate(chars)
                     if x['name'].lower() == name.lower())
        ind = next(char_iter, None)

        if ind is None:
            raise errors.DataNotFound
        else:
            return ind

    # prompt if no name given
    thumbnail = ctx.bot.get_emoji_url(config.emojis.mushping)
    msg = (f'{text or ""}React to select a character or select '
           f'\u200b \u274e \u200b to cancel\n\u200b')
    prompt = await list_chars(ctx, user, msg, thumbnail)
    ctx.bot.reply_cache.add(ctx, prompt)  # cache for clean up

    # numbered unicode emojis 1 - # max chars
    max_chars = config.core.max_chars
    reactions = {f'{x + 1}': f'{x + 1}\ufe0f\u20e3'
                 for x in range(min(len(user['chars']), max_chars))}
    reactions['x'] = '\u274e'
    sel = await ctx.bot.wait_for_reaction(ctx, prompt, reactions)

    return None if sel == 'x' else int(sel)-1


async def confirm_prompt(ctx: commands.Context, text) -> bool:
    """
    Prompt user for confirmation

    Parameters
    ----------
    ctx: commands.Context
    text: str
        text to display

    Returns
    -------
    bool
        user's selection

    """
    embed = discord.Embed(description=text, color=config.core.embed_color)
    embed.set_author(name='Confirmation', url=ctx.bot.user.avatar.url)
    thumbnail = ctx.bot.get_emoji_url(config.emojis.mushping)
    embed.set_thumbnail(url=thumbnail)
    prompt = await ctx.send(embed=embed)
    ctx.bot.reply_cache.add(ctx, prompt)  # cache for clean up

    # wait for reaction
    reactions = {'true': '\u2705', 'false': '\u274e'}
    sel = await ctx.bot.wait_for_reaction(ctx, prompt, reactions)

    return sel == 'true'  # other reactions will timeout
