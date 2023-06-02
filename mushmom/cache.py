"""
Expiring caches.  CachedCommandTree from
- https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131#file-command_tree

"""
from __future__ import annotations

import time
from typing import Any, Hashable, Dict, Optional, List, TYPE_CHECKING, Union
from collections import OrderedDict

import discord
from discord import app_commands

if TYPE_CHECKING:
    from discord.abc import Snowflake

    AppCommandStore = Dict[str, app_commands.AppCommand]  # name: AppCommand


class TTLCache:
    """
    Entries will expire after some time.  Prune auto calls every x calls
    to get/add/remove

    Parameters
    ----------
    seconds: int
        the number of seconds to wait before expiring

    """
    def __init__(self, seconds: int, max_size: Optional[int] = None):
        self.__ttl = seconds
        self.__cache = {}
        self.__cnt = 0
        self.__recur = 20  # auto prune every 20 calls

        # also max_size
        self.__max_size = max_size

    def prune(self) -> None:
        """Loop through cache and remove all expired keys"""
        current_time = time.monotonic()
        rm_time = [k for (k, (v, t)) in self.__cache.items()
                    if current_time > (t + self.__ttl)]

        # cap at max_size. oldest first
        n = self.__max_size
        filtered = [k for k in self.__cache.keys() if k not in rm_time]
        rm_size = list(reversed(filtered))[n:] if n is not None else []

        for k in rm_time + rm_size:
            del self.__cache[k]

    def get(self, k: Hashable) -> Any:
        self.__prune_n_calls()

        if k in self.__cache:
            value, t = self.__cache.get(k)
            current_time = time.monotonic()
            if current_time <= (t + self.__ttl):
                return value

    def add(self, k: Hashable, value: Any) -> None:
        self.__prune_n_calls()
        self.__cache[k] = (value, time.monotonic())

    def remove(self, k: Hashable) -> None:
        self.__prune_n_calls()
        self.__cache.pop(k, None)

    def refresh(self, k: Hashable) -> None:
        if k in self.__cache:
            value = self.__cache.pop(k)
            self.add(k, value)  # update ts

    def clear(self) -> None:
        self.__cache = {}

    def contains(self, k: Hashable) -> bool:
        if k in self.__cache:
            value, t = self.__cache.get(k)
            current_time = time.monotonic()
            return current_time <= (t + self.__ttl)
        else:
            return False

    def __contains__(self, k: Hashable) -> bool:
        return self.contains(k)

    def __iter__(self):
        self.prune()
        return iter(self.__cache)

    def __prune_n_calls(self):
        """Prune every __recur calls"""
        self.__cnt += 1

        if self.__cnt >= self.__recur:
            self.prune()
            self.__cnt = 0


class LRUCache:
    """
    Least recently used entry will pop.  Just prune when adding;
    refresh when getting and adding

    Parameters
    ----------
    max_size: int
        max number of entries

    """
    def __init__(self, max_size: int):
        self.__max_size = max_size
        self.__cache = OrderedDict()

    def prune(self) -> None:
        """Keep n entries less than max size"""
        while len(self.__cache) > self.__max_size:
            self.__cache.popitem(last=False)

    def get(self, k: Hashable) -> Any:
        self.refresh(k)
        return self.__cache.get(k)

    def add(self, k: Hashable, value: Any) -> None:
        self.__cache[k] = value
        self.refresh(k)
        self.prune()

    def remove(self, k: Hashable) -> None:
        self.__cache.pop(k, None)

    def refresh(self, k: Hashable) -> None:
        if k in self.__cache:
            self.__cache.move_to_end(k)

    def clear(self) -> None:
        self.__cache = OrderedDict()

    def contains(self, k: Hashable) -> bool:
        return k in self.__cache

    def __contains__(self, k: Hashable) -> bool:
        return self.contains(k)

    def __iter__(self):
        return iter(self.__cache)


class CachedCommandTree(app_commands.CommandTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_app_commands: AppCommandStore = {}
        # guild_id: AppCommandStore
        self._guild_app_commands: Dict[int, AppCommandStore] = {}

    def find_app_command_by_names(
            self,
            *qualified_name: str,
            guild: Optional[Union[Snowflake, int]] = None,
    ) -> Optional[app_commands.AppCommand]:
        commands = self._global_app_commands
        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not guild_commands and self.fallback_to_global:
                commands = self._global_app_commands
            else:
                commands = guild_commands

        for cmd_name, cmd in commands.items():
            if any(name in qualified_name for name in cmd_name.split()):
                return cmd

        return None

    def get_app_command(
            self,
            value: Union[str, int],
            guild: Optional[Union[Snowflake, int]] = None,
    ) -> Optional[app_commands.AppCommand]:
        def search_dict(
                d: AppCommandStore
        ) -> Optional[app_commands.AppCommand]:
            for cmd_name, cmd in d.items():
                if (value == cmd_name
                        or (str(value).isdigit() and int(value) == cmd.id)):
                    return cmd
            return None

        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not self.fallback_to_global:
                return search_dict(guild_commands)
            else:
                return (search_dict(guild_commands)
                        or search_dict(self._global_app_commands))
        else:
            return search_dict(self._global_app_commands)

    @staticmethod
    def _unpack_app_commands(
            commands: List[app_commands.AppCommand]
    ) -> AppCommandStore:
        ret: AppCommandStore = {}

        def unpack_options(
                options: List[
                    Union[app_commands.AppCommand,
                          app_commands.AppCommandGroup,
                          app_commands.Argument]
                ]
        ):
            for option in options:
                if isinstance(option, app_commands.AppCommandGroup):
                    ret[option.qualified_name] = option  # type: ignore
                    unpack_options(option.options)  # type: ignore

        for command in commands:
            ret[command.name] = command
            unpack_options(command.options)  # type: ignore

        return ret

    async def _update_cache(
            self,
            commands: List[app_commands.AppCommand],
            guild: Optional[Union[Snowflake, int]] = None
    ) -> None:
        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Optional[Snowflake] = None
        if guild is not None:
            if isinstance(guild, int):
                _guild = discord.Object(guild)
            else:
                _guild = guild

        if _guild:
            self._guild_app_commands[_guild.id] = self._unpack_app_commands(commands)
        else:
            self._global_app_commands = self._unpack_app_commands(commands)

    async def fetch_command(
            self,
            command_id: int,
            /,
            *,
            guild: Optional[Snowflake] = None
    ) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    async def fetch_commands(
            self,
            *,
            guild: Optional[Snowflake] = None
    ) -> List[app_commands.AppCommand]:
        res = await super().fetch_commands(guild=guild)
        await self._update_cache(res, guild=guild)
        return res

    def clear_app_commands_cache(self, *, guild: Optional[Snowflake]) -> None:
        if guild:
            self._guild_app_commands.pop(guild.id, None)
        else:
            self._global_app_commands = {}

    def clear_commands(
            self,
            *,
            guild: Optional[Snowflake],
            type: Optional[discord.AppCommandType] = None,
            clear_app_commands_cache: bool = True
    ) -> None:
        super().clear_commands(guild=guild)
        if clear_app_commands_cache:
            self.clear_app_commands_cache(guild=guild)

    async def sync(
            self,
            *,
            guild: Optional[Snowflake] = None
    ) -> List[app_commands.AppCommand]:
        res = await super().sync(guild=guild)
        await self._update_cache(res, guild=guild)
        return res
