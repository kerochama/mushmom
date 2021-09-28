"""
Functions related to database connection

Keep track data access for all sets, but only when getting char data

"""
import os

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

from mushmom import config

load_dotenv()  # use env variables from .env

client = AsyncIOMotorClient(os.getenv('MONGO_CONN_STR'))
db = client[config.database.name]


async def get_user(userid, proj=None):
    """

    :param userid:
    :param proj: list of fields to return
    :return:
    """
    return await db.users.find_one({'_id': userid}, proj)


async def user_exists(userid):
    # not going to update tracking
    rec = await get_user(userid, ['_id'])
    return rec is not None


async def add_user(userid, char_data: dict):
    """
    When adding user, only allow setting first char

    :param userid:
    :param char_data:
    :return:
    """
    data = {
        '_id': userid,
        'default': 0,
        'chars': [char_data],
        'create_time': datetime.utcnow(),
        'update_time': datetime.utcnow(),
        'n_access': 1
    }

    return await db['users'].insert_one(data)


async def set_user(userid, data):
    # set userid/_id manually
    data.pop('_id', None)
    data.pop('userid', None)

    # update tracking
    data['update_time'] = datetime.utcnow()
    update = {
        '$set': data,
        '$inc': {'n_access': 1}
    }

    return await db['users'].update_one({'_id': userid}, update)


async def increment_user(userid):
    """
    Keep track of how often user gets/sets data

    :param userid:
    :return:
    """
    update = {
        '$set': {'update_time': datetime.utcnow()},
        '$inc': {'n_access': 1}
    }
    return await db['users'].update_one({'_id': userid}, update)


async def get_char_data(userid):
    """
    Get users default char data (dict)

    :param userid:
    :return:
    """
    user_data = await db.users.find_one({'_id': userid})

    if user_data:
        await increment_user(userid)
        i = user_data['default']

        if user_data['chars']:
            return user_data['chars'][i]
