"""
Functions related to database connection.  Currently using MongoDB,
but could be replaced easily as long as functionality is the same

"""
import time
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.results import InsertOneResult, UpdateResult
from datetime import datetime
from typing import Optional, Union, Any, Hashable

from . import config


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
        self.user_cache = DatabaseCache(seconds=60)  # 5 minute cache

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
            self, userid: int,
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

        self.user_cache.add(userid, data)
        return await self.users.insert_one(data)

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
        self.user_cache.remove(userid)  # invalidate cache

        # set userid/_id manually
        data.pop('_id', None)
        data.pop('userid', None)
        update = {'$set': data}

        return await self.users.update_one({'_id': userid}, update)

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
        return await self.guilds.find_one({'_id': guildid}, projection)

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
            'prefixes': [],
            'channel': None,
            'create_time': datetime.utcnow(),
            'update_time': datetime.utcnow(),
        }
        _data.update(data or {})

        return await self.guilds.insert_one(_data)

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

        return await self.guilds.update_one({'_id': guildid}, update)

    async def track(
            self,
            guildid: int,
            userid: int,
            command: str
    ) -> tuple[UpdateResult, UpdateResult]:
        """
        Keep track of command calls

        Parameters
        ----------
        guildid: int
            the discord user id
        userid: int
            the discord user id
        command: str
            the command to track

        Returns
        -------
        tuple[UpdateResult, UpdateResult]
            tuple of results for updating the guild and user

        """
        update = {
            '$set': {'update_time': datetime.utcnow()},
            '$inc': {f'commands.{command}': 1}
        }

        return (
            await self.guilds.update_one({'_id': guildid}, update),
            await self.users.update_one({'_id': userid}, update)
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


class DatabaseCache:
    """
    Maintains a cache of db output to reduce calls to db when changes
    are unlikely.  Would cause issues if user makes changes in a different
    channel/server before submitting, but the user would basically know
    they were doing it.

    Entries will expire after some time.  Verify auto calls every x calls
    to get/add/remove

    Parameters
    ----------
    seconds: int
        the number of seconds to wait before expiring

    """
    def __init__(self, seconds: int):
        super().__init__()
        self.__ttl = seconds
        self.__cache = {}

        self.__cnt = 0
        self.__recur = 20  # auto verify every 20 calls

    def verify_cache_integrity(self) -> None:
        """Loop through cache and remove all expired keys"""
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__cache.items()
                     if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self.__cache[k]

    def get(self, k: Hashable) -> Any:
        self._verify_internal()

        if k in self.__cache:
            value, t = self.__cache.get(k)
            current_time = time.monotonic()
            if current_time <= (t + self.__ttl):
                return value

    def add(self, k: Hashable, value: Any) -> None:
        self._verify_internal()
        self.__cache[k] = (value, time.monotonic())

    def remove(self, k: Hashable) -> None:
        self._verify_internal()
        self.__cache.pop(k, None)

    def contains(self, k: Hashable) -> bool:
        if k in self.__cache:
            value, t = self.__cache.get(k)
            current_time = time.monotonic()
            return current_time <= (t + self.__ttl)
        else:
            return False

    def __contains__(self, k: Hashable) -> bool:
        return self.contains(k)

    def _verify_internal(self):
        """Verify every __recur calls"""
        self.__cnt += 1

        if self.__cnt >= self.__recur:
            self.verify_cache_integrity()
            self.__cnt = 0
