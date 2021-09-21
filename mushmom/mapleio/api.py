import aiohttp

from PIL import Image
from io import BytesIO

from mushmom import config


async def latest_version(region='GMS'):
    """
    Get the latest version for region

    :param region:
    :return:
    """
    u = f'{config.MAPLEIO_API}/wz'

    # http request
    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                data = await r.json()
                region_data = [x for x in data if x['isReady'] and x['region'] == region]
                latest = region_data[-1]['mapleVersionId']
            else:
                latest = '225'  # arbitrary

    return latest


async def get_item(itemid, region='GMS',
                   version=config.MAPLEIO_DEFAULT_VERSION):
    """
    Get info about itemid

    :param itemid:
    :param region:
    :param version:
    :return:
    """
    u = f'{config.MAPLEIO_API}/{region}/{version}/item/{itemid}'
    # http request
    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                data = await r.json()
            else:
                data = None

    return data


async def get_sprite(char, pose='stand1', emotion='default',
                     zoom=1, flipx=False, bgcolor=(0, 0, 0, 0)):
    """
    Make API call to get char sprite data

    :param char:
    :param pose:
    :param emotion:
    :param zoom:
    :param flipx:
    :param bgcolor:
    :return:
    """
    args = locals().copy()
    args.pop('char')
    u = char.url(**args)

    # http request
    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                return await r.read()  # png bytes


async def get_emote(char, emotion='default', zoom=1):
    """
    Make API call to get char sprite data, crop out body,
    and return bytes.  Remove cape and weapon

    :param char:
    :param emotion:
    :param zoom:
    :return:
    """
    args = locals().copy()
    args.pop('char')
    u = char.url(remove=['Cape', 'Weapon'], **args)

    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                img_data = await r.read()  # png bytes
            else:
                return  # return None

    # crop body out image
    img = Image.open(BytesIO(img_data))
    w, h = img.size
    pad = 8
    emote = img.crop((0, 0, w, h + zoom * (pad - config.MAPLEIO_BODY_HEIGHT)))
    byte_arr = BytesIO()
    emote.save(byte_arr, format='PNG')
    return byte_arr.getvalue()
