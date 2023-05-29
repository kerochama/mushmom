"""
Functions related to database connection.  Currently using MongoDB,
but could be replaced easily as long as functionality is the same

Maintains a cache of db output to reduce calls to db when changes
are unlikely.  Would cause issues if user makes changes in a different
channel/server before submitting, but the user would basically know
they were doing it.

Guild cache capped at 100.  User tracking only starts if they import or fame

"""
import asyncio

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne, DESCENDING
from pymongo.results import (
    InsertOneResult, UpdateResult, BulkWriteResult
)
from datetime import datetime
from typing import Optional, Union, Iterable

from . import config
from .cache import TTLCache, LRUCache


class Database:
    """
    User data and guild data access. Keeps track data access by user
    and guild, though double counting for get+set is handled

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
    users: AsyncIOMotorCollection
        users collection
    guilds: AsyncIOMotorCollection
        guilds collection

    """
    def __init__(self, client: AsyncIOMotorClient):
        self.client = client
        self.db = self.client[config.database.name]

        # specific collections
        self.users = self.db.users
        self.guilds = self.db.guilds

        # caches
        self.user_cache = TTLCache(seconds=300)  # 5 minute cache
        self.guild_cache = LRUCache(max_size=100)

    async def initialize_guild_cache(self):
        """Pull of 100 most currently updated guilds"""
        data = self.guilds.find({}).sort('update_time', pymongo.DESCENDING)

        for guild in await data.to_list(length=100):
            self.guild_cache.add(guild['_id'], guild)

    async def get_user(
            self,
            userid: int,
            projection: Optional[Union[list[str], dict[str, bool]]] = None,
    ) -> Optional[dict]:
        """
        Returns data for user

        Parameters
        ----------
        userid: int
            the discord user id
        projection: Optional[Union[list[str], dict[str, bool]]]
            a list of keys to be returned or a dict with {key: bool}
            (True to include, False to exclude)

        Returns
        -------
        Optional[dict]
            found user data or None

        """
        lock = asyncio.Lock()  # avoid update between in cache check and await

        async with lock:
            if userid in self.user_cache:
                _data = self.user_cache.get(userid)
                return self._handle_proj(_data, projection)
            else:
                data = await self.users.find_one({'_id': userid}, projection)
                if data:
                    self.user_cache.add(userid, data)
                return data

    async def add_user(
            self,
            userid: int,
            char_data: Optional[dict] = None
    ) -> InsertOneResult:
        """
        Add a new user to database. Only allow setting first character

        Parameters
        ----------
        userid: int
            the discord user id
        char_data: Optional[dict]
            output of Character.to_dict()

        Returns
        -------
        InsertOneResult
            the result of adding the user

        """
        chars = [char_data] if char_data else []
        data = {
            '_id': userid,
            'default': 0,
            'chars': chars,
            'fame': 0,
            'fame_log': [],
            'create_time': datetime.utcnow(),
            'update_time': datetime.utcnow(),
        }

        r = await self.users.insert_one(data)

        if r.acknowledged:
            self.user_cache.add(userid, data)

        return r

    async def set_user(
            self,
            userid: int,
            data: dict,
    ) -> UpdateResult:
        """
        Set/update user data fields.  Invalidate cache since user can
        do a partial update, which is difficult to handle

        Parameters
        ----------
        userid: int
            the discord user id
        data: dict
            keys are fields to update and values are new values

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

        r = await self.users.update_one({'_id': userid}, update)

        # update cache
        if userid in self.user_cache:
            self.user_cache.get(userid).update(data)

        return r

    async def bulk_user_update(
            self,
            ops: dict[int, dict],
            ordered: bool = False
    ) -> BulkWriteResult:
        """
        Bulk write to data users database

        Parameters
        ----------
        ops: dict[int, dict]
            userid to data mapping
        ordered: bool
            whether or not to write in order

        Returns
        -------

        """
        requests = []

        for userid, data in ops.items():
            data.pop('_id', None)
            requests.append(UpdateOne({'_id': userid}, {'$set': data}))

        r = await self.users.bulk_write(requests, ordered=ordered)

        # update cache
        for userid, data in ops.items():
            if userid in self.user_cache:
                self.user_cache.get(userid).update(data)

        return r

    async def get_guild(
            self,
            guildid: int,
            projection: Optional[Union[list[str], dict[str, bool]]] = None,
    ) -> Optional[dict]:
        """
        Returns data for guild

        Parameters
        ----------
        guildid: int
            the discord guild id
        projection: Optional[Union[list[str], dict[str, bool]]]
            a list of keys to be returned or a dict with {key: bool}
            (True to include, False to exclude)

        Returns
        -------
        Optional[dict]
            found guild data or None

        """
        lock = asyncio.Lock()  # avoid update between in cache check and await

        async with lock:
            if guildid in self.guild_cache:
                _data = self.guild_cache.get(guildid)
                return self._handle_proj(_data, projection)
            else:
                data = await self.guilds.find_one({'_id': guildid}, projection)
                if data:
                    self.guild_cache.add(guildid, data)
                return data

    async def add_guild(
            self,
            guildid: int,
            data: Optional[dict] = None
    ) -> InsertOneResult:
        """
        Add a new guild to database with provided data

        Parameters
        ----------
        guildid: int
            the discord guild id
        data: dict
            guild data to update

        Returns
        -------
        InsertOneResult
            the result of adding the guild

        """
        _data = {
            '_id': guildid,
            'channel': None,
            'create_time': datetime.utcnow(),
            'update_time': datetime.utcnow(),
        }
        _data.update(data or {})

        r = await self.guilds.insert_one(_data)

        if r.acknowledged:
            self.guild_cache.add(guildid, _data)

        return r

    async def set_guild(
            self,
            guildid: int,
            data: dict,
    ) -> UpdateResult:
        """
        Set/update guild data fields

        Parameters
        ----------
        guildid: int
            the discord guild id
        data: dict
            keys are fields to update and values are new values

        Returns
        -------
        UpdateResult
            the result of updating the guild

        Notes
        -----
        set_guild is almost never called without a prior get_guild,
        so the default tracking is `False`

        """
        # set guildid/_id manually
        data.pop('_id', None)
        data.pop('guildid', None)
        update = {'$set': data}

        r = await self.guilds.update_one({'_id': guildid}, update)

        # update cache
        if guildid in self.guild_cache:
            self.guild_cache.get(guildid).update(data)

        return r

    async def update_tracking(
            self,
            tracking: Iterable[tuple],
    ) -> tuple[BulkWriteResult, BulkWriteResult]:
        """
        Convert tracking to update

        E.g.

        {
            '00000123': {
                '$set': {'update_time': 2023-04-10T21:14:05.717+00:00},
                '$inc': {
                    'commands.mush': 3
                    'commands.list char': 2
                }
            }
        }

        Parameters
        ----------
        tracking: Iterable[tuple]
            iterable of (gid, uid, cmd, ts)

        Returns
        -------
        list[BulkWriteResult, BulkWriteResult]
            the results of updating guilds and users
        """
        guilds, users = {}, {}

        def _update(d, id, ts):  # helper to process record
            if id not in d:
                d[id] = {'$set': {'update_time': datetime.min}, '$inc': {}}

            _set, _inc = d[id]['$set'], d[id]['$inc']
            _set['update_time'] = max(_set['update_time'], ts)
            _inc[f'commands.{cmd}'] = _inc.get(f'commands.{cmd}', 0) + 1

            # emotes tracking
            if cmd == 'mush':
                emote = f"emotes.{extras['emote']}"
                _inc[f'{emote}.0'] = _inc.get(f'{emote}.0', 0) + 1
                _prev = _set.get(f'{emote}.1', datetime.min)
                _set[f'{emote}.1'] = max(_prev, ts)

        for record in tracking:
            gid, uid, cmd, ts, extras = record

            if not await self.get_guild(gid):  # mostly in cache
                await self.add_guild(gid)

            _update(guilds, gid, ts)
            _update(users, uid, ts)

        reqs_guild = [UpdateOne({'_id': k}, v) for k, v in guilds.items()]
        reqs_user = [UpdateOne({'_id': k}, v) for k, v in users.items()]

        return (
            await self.guilds.bulk_write(reqs_guild, ordered=False),
            await self.users.bulk_write(reqs_user, ordered=False)
        )

    @staticmethod
    def _handle_proj(
            d: dict,
            proj: Optional[Union[list[str], dict[str, bool]]] = None
    ):
        """
        Filter dict like MongoDB projection

        """
        filtered = d
        if isinstance(proj, list):  # make dict for consistent handling
            proj = {k: True for k in proj}

        if proj:
            keep = [k for k, v in proj.items() if v]
            filtered = {k: v for k, v in d.items() if k in keep}
            if not filtered:  # contains only Falses
                filtered = {k: v for k, v in d.items() if k not in proj.keys()}

        return filtered

    def close(self):  # not coroutine
        self.client.close()
