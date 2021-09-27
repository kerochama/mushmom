import aiohttp
import functools

from PIL import Image
from io import BytesIO

from mushmom import config


def with_session(coro):
    """
    Decorator to handle adding aiohttp session if not provided

    :param coro:
    :return:
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
async def latest_version(region='GMS', session=None):
    """
    Get the latest version for region

    :param region:
    :param session:
    :return:
    """
    u = f'{config.MAPLEIO_API}/wz'

    async with session.get(u) as r:
        if r.status == 200:
            data = await r.json()
            region_data = [x for x in data if x['isReady'] and x['region'] == region]
            latest = region_data[-1]['mapleVersionId']
        else:
            latest = '225'  # arbitrary

    return latest


@with_session
async def get_item(itemid, region='GMS',
                   version=config.MAPLEIO_DEFAULT_VERSION,
                   session=None):
    """
    Get info about itemid

    :param itemid:
    :param region:
    :param version:
    :param session:
    :return:
    """
    u = f'{config.MAPLEIO_API}/{region}/{version}/item/{itemid}'

    # http request
    async with session.get(u) as r:
        if r.status == 200:
            return await r.json()


@with_session
async def get_sprite(char, pose='stand1', emotion='default',
                     zoom=1, flipx=False, bgcolor=(0, 0, 0, 0),
                     session=None):
    """
    Make API call to get char sprite data

    :param char:
    :param pose:
    :param emotion:
    :param zoom:
    :param flipx:
    :param bgcolor:
    :param session:
    :return:
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
async def get_emote(char, emotion='default', zoom=1, pad=8, session=None):
    """
    Make API call to get char sprite data, crop out body,
    and return bytes.  Remove cape and weapon

    :param char:
    :param emotion:
    :param zoom:
    :param pad:
    :param session:
    :return:
    """
    u = char.url(emotion=emotion, zoom=zoom, remove=['Cape', 'Weapon'])

    async with session.get(u) as r:
        if r.status == 200:
            img_data = await r.read()  # png bytes

            # crop body out image
            img = Image.open(BytesIO(img_data))
            w, h = img.size

            scaled_body_height = zoom * (config.MAPLEIO_BODY_HEIGHT - pad)
            emote = img.crop((0, 0, w, h - scaled_body_height))
            byte_arr = BytesIO()
            emote.save(byte_arr, format='PNG')

            return byte_arr.getvalue()
