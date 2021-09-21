import os

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env

client = AsyncIOMotorClient(os.getenv('MONGO_CONN_STR'))
db = client.mushmom


async def get_user(userid, proj=None):
    """

    :param userid:
    :param proj: list of fields to return
    :return:
    """
    return await db.users.find_one({'_id': userid}, proj)


async def user_exists(userid):
    rec = await get_user(userid, ['_id'])
    return rec is not None


async def get_char_data(userid):
    """
    Get users default char data (dict)

    :param userid:
    :return:
    """
    user_data = await db.users.find_one({'_id': userid})

    if user_data:
        i = user_data['default']
        return user_data['chars'][i]


# change to add and set user.  also consider User class
async def update_user(userid, data):
    # set userid/_id manually
    data.pop('_id', None)
    data.pop('userid', None)

    if await user_exists(userid):
        await db['users'].update_one({'id': userid}, {'$set': data})
    else:
        await db['users'].insert_one({'_id': userid}, data)
