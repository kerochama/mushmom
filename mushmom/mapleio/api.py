"""
Functions related to making API calls to maplestory.io

"""
import aiohttp
import asyncio
import functools
import zipfile

from PIL import Image, ImageOps
from io import BytesIO
from typing import Callable, Coroutine, Any, Optional, Union, Iterable

from . import imutils
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
        expression: Optional[str] = None,
        zoom: float = 1,
        pad: int = 8,
        min_width: int = 0,
        session: aiohttp.ClientSession = None
) -> Optional[bytes]:
    """
    Make API call to get char sprite data, crop out body, and return
    bytes.  Remove cape and weapon

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    expression: str
        expression from expressions.json. If None, use default
    zoom: float
        how zoomed in the image should be (1 = 100%)
    pad: int
        number of pixels to pad below head to show body
    min_width: int
        min width of image. padded on right with transparent fill
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[bytes]
        the byte data from the generated emote

    """
    expression = expression or char.expression
    u = char.url(
        pose='stand1',
        expression=expression,
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
            cropped = img.crop((0, 0, w, h - scaled_body_height))
            emote = imutils.min_width(cropped, min_width)

            byte_arr = BytesIO()
            emote.save(byte_arr, format='PNG')

            return byte_arr.getvalue()


@with_session
async def get_sprite(
        char: 'Character',
        pose: Optional[str] = None,
        expression: Optional[str] = None,
        frame: Union[int, str] = 0,
        zoom: float = 1,
        flipx: bool = False,
        bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
        render_mode: Optional[str] = None,
        hide: Optional[Iterable[str]] = None,
        remove: Optional[Iterable[str]] = None,
        replace: Optional[Iterable['Equip']] = None,
        min_width: int = 0,
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
    expression: str
        expression from expressions.json. If None, use default
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
    min_width: int
        min width of image. padded on right with transparent fill
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[bytes]
        the byte data from the generated sprite

    """
    pose = pose or char.pose
    expression = expression or char.expression

    args = locals().copy()
    args.pop('char')
    args.pop('min_width')
    args.pop('session')
    u = char.url(**args)

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            img_data = await r.read()  # png bytes
            img = Image.open(BytesIO(img_data))
            padded = imutils.min_width(img, min_width)

            byte_arr = BytesIO()
            padded.save(byte_arr, format='PNG')

            return byte_arr.getvalue()


@with_session
async def get_layers(
        char: 'Character',
        pose: Optional[str] = None,
        expression: Optional[str] = None,
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
    expression: str
        expression from expressions.json. If None, use default
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
    expression = expression or char.expression

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
        expression: Optional[str] = None,
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
    expression: str
        expression from expressions.json. If None, use default
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
    expression = expression or char.expression

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


@with_session
async def get_animated_emote(
        char: 'Character',
        expression: Optional[str] = None,
        zoom: float = 1,
        pad: int = 8,
        duration: Union[int, Iterable[int]] = 180,
        min_width: int = 0,
        session: aiohttp.ClientSession = None
) -> Optional[bytes]:
    """

    Parameters
    ----------
    char: Character
        The character from which to generate the sprite
    expression: str
        expression from expressions.json. If None, use default
    zoom: float
        how zoomed in the image should be (1 = 100%)
    pad: int
        number of pixels to pad below head to show body
    duration: Union[int, Iterable[int]]
        ms per frame. 180 is duration for walk1
    min_width: int
        min width of image. padded on right with transparent fill
    session: Optional[aiohttp.ClientSession]
        session to use when issuing http get

    Returns
    -------
    Optional[bytes]
        the byte data from the generated emote

    """
    expression = expression or char.expression
    equips = char.filtered_equips()

    # divide char parts into groups
    remove = ['Cape', 'Weapon', 'Shoes']  # can all go below feet
    head = ['Head', 'Face', 'Hair', 'Hat',
            'Face Accessory', 'Eye Decoration', 'Earrings']
    body = ['Body'] + [eq.type for eq in equips if eq.type not in head+remove]

    # API calls for static body and head frames
    kwargs = {
        'char': char,
        'pose': 'stand1',
        'expression': expression,
        'zoom': zoom,
        'hide': head,
        'remove': remove,
        'session': session
    }

    _base = await get_sprite(**kwargs)
    kwargs['hide'] = body
    _head_frames = await get_frames(**kwargs)

    if _base and _head_frames:
        base = Image.open(BytesIO(_base))
        head_frames = [Image.open(BytesIO(x)) for x in _head_frames]

        # calc max size
        w, h = (max(f.width for f in head_frames),
                max(f.height for f in head_frames))

        # combine to create frames
        # ideally use FeetCenter, but horizontally 1 pixel off
        frames = []
        for f in head_frames:
            im = Image.new('RGBA', (w, h), (0, )*4)  # aligning top right
            im.paste(f, (w - f.width, 0))
            im.paste(base, (w - base.width, 0), mask=base)

            # crop to head
            scaled_body_height = zoom * (config.mapleio.body_height - pad)
            cropped = im.crop((0, 0, w, h - scaled_body_height))
            emote = imutils.thresh_alpha(cropped, 64)
            frames.append(imutils.min_width(emote, min_width))

        byte_arr = BytesIO()
        frames[0].save(byte_arr, format='GIF', save_all=True, loop=0,
                       append_images=frames[1:], duration=duration, disposal=2)

        return byte_arr.getvalue()
