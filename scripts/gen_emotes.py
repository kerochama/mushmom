"""
Generate emote files for docs

$python3 -m scripts.gen_emotes gen_emotes
$python3 -m scripts.gen_emotes gen_emotes_preview


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


def gen_emotes_preview(
        emotes: list[tuple[str, Image]],
        cols: int = 6,
        cell_size: tuple[int, int] = (75, 90),
        save = True
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
    save: bool
        whether or not to save

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
            draw.fontmode = '1'
            font = ImageFont.truetype('/Library/Fonts/Arial.ttf', 10)
            _, _, tw, th = draw.textbbox((0, 0), name, font)
            tpos = ((w - tw)//2, h - th - 10)
            draw.text(tpos, name, font=font, fill='silver')

            # update base
            padded = Image.new('RGBA', base.size, (0, )*4)
            padded.paste(cell, (j * w, i * h))
            base = Image.alpha_composite(base, padded)

    if save:
        base.save(f'{ROOT}/emotes_preview.png', format='PNG')

    return base


def gen_animated_emotes_preview(
        emotes: list[tuple[str, Image]],
        cols: int = 6,
        cell_size: tuple[int, int] = (75, 90)
):
    """
    Generate a table of labeled animated emotes

    Algorithm:
        loop through all emotes in increments of 10. Only create new result
        frame when one emote needs to flip to a new frame (passes its
        duration).  Otherwise just increase the duration of the current frame

    Parameters
    ----------
    emotes: list[tuple[str, Image]]
        list of emotes
    cols: int
        number of emotes per row
    cell_size: tuple[int, int]
        (width, height) pixels

    """
    states = [EmoteState(*info) for info in emotes]
    _emotes = [state.emote() for state in states]
    kwargs = dict(cols=cols, cell_size=cell_size, save=False)
    frames = [gen_emotes_preview(_emotes, **kwargs)]
    inc = 10
    durs = [inc]

    i = 1
    while not all([state.complete() for state in states]):
        print(f'iter: {i}', end='\r')
        new_frame = False

        for state in states:
            if state.curr_dur == state.img.info['duration']:  # cycle to next frame
                state.next()
                state.curr_dur = 0
                new_frame = True

            state.curr_dur += inc

        if new_frame:
            _emotes = [state.emote() for state in states]
            frames.append(gen_emotes_preview(_emotes, **kwargs))
            durs.append(inc)
        else:
            durs[-1] += inc

        i += 1

    filename = f'{ROOT}/animated_emotes_preview.gif'
    frames[0].save(filename, format='GIF', save_all=True, loop=0,
                   append_images=frames[1:], duration=durs, disposal=2)


class EmoteState:
    def __init__(self, name, img):
        self.name = name
        self.img = img
        self.curr_dur = 0

    def complete(self) -> bool:
        """Whether or not the emote has been fully cycled"""
        return (self.img.tell() + 1 == self.img.n_frames
                and self.curr_dur == self.img.info['duration'])

    def emote(self) -> tuple[str, Image]:
        """Return tuple of current emote frame"""
        return self.name, self.img.convert('RGBA')

    def next(self):
        """Cycle to next frame"""
        self.img.seek((self.img.tell() + 1) % self.img.n_frames)


if __name__ == "__main__":
    script, option = sys.argv  # only 1 arg allowed

    if option == 'gen_emote':
        with open('sample/sample_url.txt', 'r') as f:
            url = f.read()

        char = Character.from_url(url)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(gen_emotes(char))
    elif option == 'gen_emotes_preview':
        files = os.listdir(f'{ROOT}/static')
        files.sort()
        emotes = []

        for file in files:
            emote, ext = file.split('.')
            img = Image.open(f'{ROOT}/static/{file}')
            emotes.append((emote, img))

        gen_emotes_preview(emotes)
    elif option == 'gen_animated_emotes_preview':
        files = os.listdir(f'{ROOT}/animated')
        files.sort()
        emotes = []

        for file in files:
            emote, ext = file.split('.')
            img = Image.open(f'{ROOT}/animated/{file}')
            emotes.append((emote, img))

        gen_animated_emotes_preview(emotes)
