"""
Generate emote files for docs

$python3 -m scripts.gen_emotes gen_emotes
$python3 -m scripts.gen_emotes gen_emote_preview


"""

import asyncio
import aiohttp
import math
import sys
import os

from typing import Optional
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont

from mushmom.cogs import mush
from mushmom.mapleio.api import with_session
from mushmom.mapleio.character import Character

ROOT = 'imgs/mush'


@with_session
async def gen_emotes(char: Character, session: Optional[aiohttp.ClientSession]):
    """
    Write out a file for every emote

    Parameters
    ----------
    char: Character
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    """
    _bot = SimpleNamespace(session=session)
    cog = mush.Mush(bot=_bot)

    emotes = mush.EMOTES
    print(f'Generating {len(emotes)} emotes')

    for i, emote in enumerate(emotes):
        file = await cog._generate_emote(emote, char, min_width=0)
        _, ext = file.filename.split('.')
        path = f"{ROOT}/{'animated' if ext == 'gif' else 'static'}"

        with open(f'{path}/{emote}.{ext}', 'wb') as f:
            f.write(file.fp.getbuffer())

        print(f'{i+1}. {path}/{emote}.{ext}')


def gen_emote_preview(
        emotes: list[tuple[str, Image]],
        cols: int = 8,
        cell_size: tuple[int, int] = (75, 90)
):
    """
    Generate a table of labeled emotes

    Parameters
    ----------
    emotes: list[tuple[str, Image]]
        list of emotes
    cols: int
        number of emotes per row
    cell_size: tuple[int, int]
        (width, height) pixels

    """
    rows = math.ceil(len(emotes)/cols)
    tab = [emotes[i*cols:(i+1)*cols] for i in range(rows)]
    w, h = cell_size
    base = Image.new('RGBA', (w * cols, h * rows), (0,)*4)

    # build image
    for i, row in enumerate(tab):
        for j, emote in enumerate(row):
            name, img = emote
            cell = Image.new('RGBA', (w, h), (0,)*4)
            pos = ((w - img.width)//2, (h - img.height)//2 - 10)
            cell.paste(img, pos, mask=img)

            # add label
            draw = ImageDraw.Draw(cell)
            font = ImageFont.truetype('/Library/Fonts/Arial.ttf', 10)
            _, _, tw, th = draw.textbbox((0, 0), name, font)
            tpos = ((w - tw)//2, h - th - 10)
            draw.text(tpos, name, font=font, fill='silver')

            # update base
            padded = Image.new('RGBA', base.size, (0, )*4)
            padded.paste(cell, (j * w, i * h))
            base = Image.alpha_composite(base, padded)


    base.show()


if __name__ == "__main__":
    script, option = sys.argv  # only 1 arg allowed

    if option == 'gen_emote':
        with open('sample/sample_url.txt', 'r') as f:
            url = f.read()

        char = Character.from_url(url)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(gen_emotes(char))
    elif option == 'gen_emote_preview':
        files = os.listdir(f'{ROOT}/static')
        files.sort()
        emotes = []

        for file in files:
            emote, ext = file.split('.')
            img = Image.open(f'{ROOT}/static/{file}')
            emotes.append((emote, img))

        gen_emote_preview(emotes)