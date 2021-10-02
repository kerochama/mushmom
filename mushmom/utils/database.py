"""
Functions related to database connection.  Keep track data access for all sets,
but only when getting char data

Requires database have `users` and `guilds` collections.  MongoDB autocreates
when writing if does not exist, though

"""
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

from .. import config


class Database:
    def __init__(self, client: AsyncIOMotorClient):
        """
        Wrapper for common database calls. Using MongoDB

        :param client:
        """
        self.client = client
        self.db = self.client[config.database.name]

    async def get_user(self, userid, proj=None):
        """

        :param userid:
        :param proj: list of fields to return
        :return:
        """
        return await self.db.users.find_one({'_id': userid}, proj)

    async def user_exists(self, userid):
        # not going to update tracking
        rec = await self.get_user(userid, ['_id'])
        return rec is not None

    async def add_user(self, userid, char_data: dict):
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

        return await self.db.users.insert_one(data)

    async def set_user(self, userid, data):
        # set userid/_id manually
        data.pop('_id', None)
        data.pop('userid', None)

        # update tracking
        data['update_time'] = datetime.utcnow()
        update = {
            '$set': data,
            '$inc': {'n_access': 1}
        }

        return await self.db.users.update_one({'_id': userid}, update)

    async def increment_user(self, userid):
        """
        Keep track of how often user gets/sets data

        :param userid:
        :return:
        """
        update = {
            '$set': {'update_time': datetime.utcnow()},
            '$inc': {'n_access': 1}
        }
        return await self.db.users.update_one({'_id': userid}, update)

    async def get_char_data(self, userid):
        """
        Get users default char data (dict)

        :param userid:
        :return:
        """
        user_data = await self.get_user(userid)

        if user_data:
            await self.increment_user(userid)
            i = user_data['default']

            if user_data['chars']:
                return user_data['chars'][i]

    def close(self):  # not coroutine
        self.client.close()
