"""
Functions related to making API calls to maplestory.io

"""
import aiohttp
import functools

from PIL import Image
from io import BytesIO
from typing import Callable, Coroutine, Any, Optional, Union

from .. import config


def with_session(coro: Callable[[Any, Any], Coroutine[Any, Any, Any]]):
    """
    Decorator to handle adding aiohttp session if not provided

    Parameters
    ----------
    coro: Callable[[Any, Any], Coroutine[Any, Any, Any]]

    Returns
    -------

    """
    @functools.wraps(coro)
    async def wrapper(*args, **kwargs):
        if 'session' not in kwargs or kwargs['session'] is None:
            kwargs.pop('session', None)
            async with aiohttp.ClientSession() as session:
                ret = await coro(session=session, *args, **kwargs)
        else:
            ret = await coro(*args, **kwargs)
        return ret
    return wrapper


@with_session
async def latest_version(
        region: str = 'GMS',
        session: Optional[aiohttp.ClientSession] = None
) -> str:
    """
    Get the latest version for region

    Parameters
    ----------
    region: str
        maplestory region
    session: session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    str
        the latest version found

    """
    u = f'{config.mapleio.api_url}/wz'

    async with session.get(u) as r:
        if r.status == 200:
            data = await r.json()
            region_data = [x for x in data if x['isReady'] and x['region'] == region]
            latest = region_data[-1]['mapleVersionId']
        else:
            latest = '225'  # arbitrary

    return latest


@with_session
async def get_item(
        itemid: Union[int, str],
        region: str = 'GMS',
        version: str = config.mapleio.default_version,
        session: aiohttp.ClientSession = None
) -> dict:
    """
    Get info about itemid

    Parameters
    ----------
    itemid: Union[int, str]
        the item's id
    region: str
        region to pull info from
    version: str
        version to pull info from
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    dict
        the json returned by maplestory.io

    """
    u = f'{config.mapleio.api_url}/{region}/{version}/item/{itemid}'

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            return await r.json()


@with_session
async def get_sprite(
        char: 'Character',
        pose: str = 'stand1',
        emotion: str = 'default',
        zoom: float = 1,
        flipx: bool = False,
        bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
        session: aiohttp.ClientSession = None
) -> bytes:
    """
    Make API call to get char sprite data

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    pose: str
        pose from poses.json
    emotion: str
        emotion from emotions.json
    zoom: float
        how zoomed in the image should be (1 = 100%)
    flipx: bool
        whether or not to flip sprite horizontally
    bgcolor: tuple[int, int, int, int]
        rgba color tuple
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    bytes
        the byte data from the generated sprite

    """
    args = locals().copy()
    args.pop('char')
    args.pop('session')
    u = char.url(**args)

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            return await r.read()  # png bytes


@with_session
async def get_emote(
        char: 'Character',
        emotion: str = 'default',
        zoom: float = 1,
        pad: int = 8,
        session: aiohttp.ClientSession = None
) -> bytes:
    """
    Make API call to get char sprite data, crop out body, and return
    bytes.  Remove cape and weapon

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    emotion: str
        emotion from emotions.json
    zoom: float
        how zoomed in the image should be (1 = 100%)
    pad: int
        number of pixels to pad below head to show body
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    bytes
        the byte data from the generated emote

    """
    u = char.url(emotion=emotion, zoom=zoom, remove=['Cape', 'Weapon'])

    async with session.get(u) as r:
        if r.status == 200:
            img_data = await r.read()  # png bytes

            # crop body out image
            img = Image.open(BytesIO(img_data))
            w, h = img.size

            scaled_body_height = zoom * (config.mapleio.body_height - pad)
            emote = img.crop((0, 0, w, h - scaled_body_height))
            byte_arr = BytesIO()
            emote.save(byte_arr, format='PNG')

            return byte_arr.getvalue()
