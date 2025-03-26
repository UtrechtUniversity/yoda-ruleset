__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import traceback
from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    import rule


class CachedDataManager:
    """This class contains a framework that subclasses can use
       to create a manager for cached data. The basic idea is that
       the subclass defines functions to access some data (e.g. in AVUs
       on particular iRODS objects). The responses are then cached.
    """

    def _get_cached_data_encoding(self) -> str:
        """Returns encoding of data used in the cache."""
        return "utf-8"

    # Internal methods to implement by subclass
    def _get_context_string(self) -> None:
        """This function should be implemented by subclasses.

        It should return a string that is used in keys to identify the subclass.

        :raises Exception: if function has not been implemented in subclass.
        """
        raise Exception("Context string not provided by CacheDataManager.")

    def _get_original_data(self, ctx: 'rule.Context', keyname: str) -> None:
        """This function is called when data needs to be retrieved from the original
           (non-cached) location.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: Name of the key

           :raises Exception: if function has not been implemented in subclass.
        """
        raise Exception("Get original data not implemented by CacheDataManager,")

    def _put_original_data(self, ctx: 'rule.Context', keyname: str, data: str) -> None:
        """This function is called when data needs to be updated in the original
           (non-cached) location.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
           :param data:    data to store for this key

           :raises Exception: if function has not been implemented in subclass.
        """
        raise Exception("Put original data not implemented by CacheDataManager.")

    # Internal methods that have a default implementation. Can optionally
    # be re-implemented by subclass.

    def __init__(self, *args: str, **kwargs: int) -> None:
        try:
            self._connection = redis.Redis(host="localhost")
        except BaseException:
            print("Error: opening Redis ARB connection failed with exception: " + traceback.format_exc())
            self._connection = None  # type: ignore[assignment]

    def _get_connection(self) -> redis.Redis:
        return self._connection

    def _cache_available(self) -> bool:
        if self._connection is None:
            return False

        try:
            return self._connection.ping()
        except BaseException:
            return False

    def _get_cache_keyname(self, keyname: str) -> str:
        return self._get_context_string() + "::" + keyname  # type: ignore[func-returns-value]

    def get(self, ctx: 'rule.Context', keyname: str) -> str:
        """Retrieves data from the cache if possible, otherwise retrieves the original.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key

        :returns: Data for this key
        """
        connection = self._get_connection()
        cache_keyname = self._get_cache_keyname(keyname)

        if self._cache_available():
            cached_result = connection.get(cache_keyname)
        else:
            cached_result = None

        if cached_result is None:
            original_result = self._get_original_data(ctx, keyname)  # type: ignore[func-returns-value]
            if self._should_populate_cache_on_get() and self._cache_available():
                self._update_cache(ctx, keyname, original_result)
            return original_result
        else:
            return cached_result.decode(self._get_cached_data_encoding())

    def put(self, ctx: 'rule.Context', keyname: str, data: str) -> None:
        """Update both the original value and cached value (if cache is not available, it is not updated).

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key
        :param data:    Data for this key
        """
        self._put_original_data(ctx, keyname, data)
        if self._cache_available():
            self._update_cache(ctx, keyname, data)

    def _update_cache(self, ctx: 'rule.Context', keyname: str, data: str) -> None:
        """Update a value in the cache.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key
        :param data:    Data for this key
        """
        cache_keyname = self._get_cache_keyname(keyname)
        self._get_connection().set(cache_keyname, data)

    def clear(self, ctx: 'rule.Context', keyname: str) -> None:
        """Clears cached data for a key if present.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key
        """
        cache_keyname = self._get_cache_keyname(keyname)
        self._get_connection().delete(cache_keyname)

    def _should_populate_cache_on_get(self) -> bool:
        """This function controls whether the manager populates the cache after retrieving original data.

        :returns: boolean value that determines whether the data manager populates
                  the cache after retrieving data
        """
        return False
