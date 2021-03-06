"""
Functions related to making API calls to maplestory.io

"""
import aiohttp
import asyncio
import functools
import zipfile

from PIL import Image
from io import BytesIO
from collections import namedtuple
from typing import Callable, Coroutine, Any, Optional, Union, Iterable

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
            latest = config.mapleio.default_version

    return latest


@with_session
async def get_item(
        itemid: Union[int, str],
        region: str = 'GMS',
        version: str = config.mapleio.default_version,
        session: aiohttp.ClientSession = None
) -> Optional[dict]:
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
    Optional[dict]
        the json returned by maplestory.io

    """
    u = f'{config.mapleio.api_url}/{region}/{version}/item/{itemid}'

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            return await r.json()


@with_session
async def get_emote(
        char: 'Character',
        emotion: Optional[str] = None,
        zoom: float = 1,
        pad: int = 8,
        session: aiohttp.ClientSession = None
) -> Optional[bytes]:
    """
    Make API call to get char sprite data, crop out body, and return
    bytes.  Remove cape and weapon

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    emotion: str
        emotion from emotions.json. If None, use default
    zoom: float
        how zoomed in the image should be (1 = 100%)
    pad: int
        number of pixels to pad below head to show body
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[bytes]
        the byte data from the generated emote

    """
    emotion = emotion or char.emotion
    u = char.url(
        pose='stand1',
        emotion=emotion,
        zoom=zoom,
        remove=['Cape', 'Weapon']
    )

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


@with_session
async def get_sprite(
        char: 'Character',
        pose: Optional[str] = None,
        emotion: Optional[str] = None,
        frame: Union[int, str] = 0,
        zoom: float = 1,
        flipx: bool = False,
        bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
        render_mode: Optional[str] = None,
        hide: Optional[Iterable[str]] = None,
        remove: Optional[Iterable[str]] = None,
        replace: Optional[Iterable['Equip']] = None,
        session: aiohttp.ClientSession = None
) -> Optional[bytes]:
    """
    Make API call to get char sprite data

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    pose: str
        pose from poses.json. If None, use default
    emotion: str
        emotion from emotions.json. If None, use default
    frame: Union[int, str]
            the animation frame. animated for gif
    zoom: float
        how zoomed in the image should be (1 = 100%)
    flipx: bool
        whether or not to flip sprite horizontally
    bgcolor: tuple[int, int, int, int]
        rgba color tuple
    render_mode: Optional[str]
            the render mode (e.g. centered, NavelCenter, etc.)
    hide: Optional[Iterable[str]]
            list of equip types to hide (alpha = 0, but still affects size)
    remove: Optional[Iterable[str]]
        list of equip types to remove
    replace: Optional[Iterable[Equip]]
        list of equip to overwrite char equips by type
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[bytes]
        the byte data from the generated sprite

    """
    pose = pose or char.pose
    emotion = emotion or char.emotion

    args = locals().copy()
    args.pop('char')
    args.pop('session')
    u = char.url(**args)

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            return await r.read()  # png bytes


@with_session
async def get_layers(
        char: 'Character',
        pose: Optional[str] = None,
        emotion: Optional[str] = None,
        frame: Union[int, str] = 0,
        zoom: float = 1,
        flipx: bool = False,
        bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
        render_mode: Optional[str] = None,
        hide: Optional[Iterable[str]] = None,
        remove: Optional[Iterable[str]] = None,
        replace: Optional[Iterable['Equip']] = None,
        session: aiohttp.ClientSession = None
) -> Optional[tuple[bytes]]:
    """
    Get background (cape) and foreground (everything else) layers.
    Also takes all parameters that can be passed to get_sprite

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    pose: str
        pose from poses.json. If None, use default
    emotion: str
        emotion from emotions.json. If None, use default
    frame: Union[int, str]
            the animation frame. animated for gif
    zoom: float
        how zoomed in the image should be (1 = 100%)
    flipx: bool
        whether or not to flip sprite horizontally
    bgcolor: tuple[int, int, int, int]
        rgba color tuple
    render_mode: Optional[str]
            the render mode (e.g. centered, NavelCenter, etc.)
    hide: Optional[Iterable[str]]
            list of equip types to hide (alpha = 0, but still affects size)
    remove: Optional[Iterable[str]]
        list of equip types to remove
    replace: Optional[Iterable[Equip]]
        list of equip to overwrite char equips by type
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    tuple[bytes]
        tuple of foreground and background

    """
    pose = pose or char.pose
    emotion = emotion or char.emotion

    args = locals().copy()
    args.pop('hide')

    # separate hide lists
    hide = hide or []
    hide_bg = set([eq.type for eq in char.filtered_equips(remove=['Cape'])]
                  + ['Body', 'Head'] + hide)
    hide_fg = set(['Cape'] + hide)

    # make http requests
    tasks = [get_sprite(hide=hide_fg, **args),
             get_sprite(hide=hide_bg, **args)]
    data = await asyncio.gather(*tasks)

    if all([x is not None for x in data]):
        return data  # [fg, bg]


@with_session
async def get_frames(
        char: 'Character',
        pose: Optional[str] = None,
        emotion: Optional[str] = None,
        frame: Union[int, str] = 0,
        zoom: float = 1,
        flipx: bool = False,
        bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
        render_mode: Optional[str] = None,
        hide: Optional[Iterable[str]] = None,
        remove: Optional[Iterable[str]] = None,
        replace: Optional[Iterable['Equip']] = None,
        session: aiohttp.ClientSession = None
) -> Optional[list[bytes]]:
    """
    Gets all frames for given specifications by downloading zip in
    memory and returning the sorted images

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    pose: str
        pose from poses.json. If None, use default
    emotion: str
        emotion from emotions.json. If None, use default
    frame: Union[int, str]
            the animation frame. animated for gif
    zoom: float
        how zoomed in the image should be (1 = 100%)
    flipx: bool
        whether or not to flip sprite horizontally
    bgcolor: tuple[int, int, int, int]
        rgba color tuple
    render_mode: Optional[str]
            the render mode (e.g. centered, NavelCenter, etc.)
    hide: Optional[Iterable[str]]
            list of equip types to hide (alpha = 0, but still affects size)
    remove: Optional[Iterable[str]]
        list of equip types to remove
    replace: Optional[Iterable[Equip]]
        list of equip to overwrite char equips by type
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[list[bytes]]

    """
    pose = pose or char.pose
    emotion = emotion or char.emotion

    args = locals().copy()
    args.pop('char')
    args.pop('session')
    u = char.url(**args)

    # modify url. could use urlparse, but fairly simple
    u = u.replace(f'{pose}/{frame}', 'download')
    u += '&format=2'  # min spritesheet

    async with session.get(u) as r:
        if r.status != 200:
            return

        frames = []
        with zipfile.ZipFile(BytesIO(await r.read())) as _zip:
            for item in _zip.filelist:
                fpose, fframe = item.filename.split('.')[0].split('_')[:2]
                if fpose == pose:
                    frames.append((_zip.read(item.filename), fframe))

        frames.sort(key=lambda x: x[1])  # sort by frame
        return [data for data, _ in frames]


@with_session
async def get_frame_layers():
    pass
