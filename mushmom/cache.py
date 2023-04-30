"""
Expiring cache

"""
import time
from typing import Any, Hashable


class TTLCache:
    """
    Entries will expire after some time.  Prune auto calls every x calls
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
        self.__recur = 20  # auto prune every 20 calls

    def prune(self) -> None:
        """Loop through cache and remove all expired keys"""
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.__cache.items()
                     if current_time > (t + self.__ttl)]
        for k in to_remove:
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
