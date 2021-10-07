"""
Functions related to database connection.  Currently using MongoDB,
but could be replaced easily as long as functionality is the same

"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.results import InsertOneResult, UpdateResult
from datetime import datetime
from typing import Optional, Union

from .. import config


class Database:
    """
    User data and guild data access. Keeps track data access by user,
    though double counting for getting then setting is handled

    Requires database have `users` and `guilds` collections.  MongoDB
    auto-creates when writing if does not exist, though

    Parameters
    ----------
    client: AsyncIOMotorClient
        a client for communicating with database

    Attributes
    ----------
    db: AsyncIOMotorDatabase
        the MongoDB database holding collections

    """
    def __init__(self, client: AsyncIOMotorClient):
        self.client = client
        self.db = self.client[config.database.name]

    async def get_user(
            self,
            userid: int,
            projection: Optional[Union[list[str], dict[str, bool]]] = None,
            track: bool = True
    ) -> Optional[dict]:
        """
        Returns data for user

        Parameters
        ----------
        userid: int
            the discord user's id
        projection: Optional[Union[list[str], dict[str, bool]]]
            a list of keys to be returned or a dict with {key: bool}
            (True to include, False to exclude)
        track: bool
            whether or not to track this call. mostly used to prevent
            double counting

        Returns
        -------
        Optional[dict]
            found user data or None

        """
        if track:
            await self.increment_user(userid)

        return await self.db.users.find_one({'_id': userid}, projection)

    async def add_user(self, userid: int, char_data: dict) -> InsertOneResult:
        """
        Add a new user to database. Only allow setting first character

        Parameters
        ----------
        userid: int
            the discord user's id
        char_data: dict
            output of Character.to_dict()

        Returns
        -------
        InsertOneResult
            the result of adding the user

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

    async def set_user(
            self,
            userid: int,
            data: dict,
            track: bool = False
    ) -> UpdateResult:
        """
        Set/update user data fields

        Parameters
        ----------
        userid: int
            the discord user's id
        data: dict
            keys are fields to update and values are new values
        track: bool
            whether or not to track this call. mostly used to prevent
            double counting

        Returns
        -------
        UpdateResult
            the result of updating the user

        Notes
        -----
        set_user is almost never called without a prior get_user,
        so the default tracking is `False`

        """
        # set userid/_id manually
        data.pop('_id', None)
        data.pop('userid', None)
        update = {'$set': data}

        # update tracking
        if track:
            data['update_time'] = datetime.utcnow()  # note: updates reference
            update['$inc'] = {'n_access': 1}

        return await self.db.users.update_one({'_id': userid}, update)

    async def increment_user(self, userid):
        """
        Updates user access tracking. For now, just keeping track of
        overall times a user access the database

        Parameters
        ----------
        userid: int
            the discord user's id

        Returns
        -------

        """
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

    def close(self):  # not coroutine
        self.client.close()
