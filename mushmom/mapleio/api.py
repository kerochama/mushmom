import json
import aiohttp

API = "https://maplestory.io/api"


async def latest_version(region='GMS'):
    """
    Get the latest version for region

    :param region:
    :return:
    """
    u = f'{API}/wz'

    # http request
    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                data = json.loads(await r.text())
                region_data = [x for x in data if x['isReady'] and x['region'] == region]
                latest = region_data[-1]['mapleVersionId']
            else:
                latest = '225'  # arbitrary

    return latest


async def get_item(itemid, region='GMS', version=None):
    """
    Get info about itemid

    :param itemid:
    :param region:
    :param version:
    :return:
    """
    u = f'{API}/{region}/{version}/item/{itemid}'

    # http request
    async with aiohttp.ClientSession() as session:
        async with session.get(u) as r:
            if r.status == 200:
                data = json.loads(await r.text())
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
