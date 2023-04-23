"""
Expiring cache

"""
import time
from typing import Any, Hashable


class TTLCache:
    """
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
        self.__verify_internal()

        if k in self.__cache:
            value, t = self.__cache.get(k)
            current_time = time.monotonic()
            if current_time <= (t + self.__ttl):
                return value

    def add(self, k: Hashable, value: Any) -> None:
        self.__verify_internal()
        self.__cache[k] = (value, time.monotonic())

    def remove(self, k: Hashable) -> None:
        self.__verify_internal()
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

    def __verify_internal(self):
        """Verify every __recur calls"""
        self.__cnt += 1

        if self.__cnt >= self.__recur:
            self.verify_cache_integrity()
            self.__cnt = 0
