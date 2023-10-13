# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import traceback

import redis


class CachedDataManager(object):
    """This class contains a framework that subclasses can use
       to create a manager for cached data. The basic idea is that
       the subclass defines functions to access some data (e.g. in AVUs
       on particular iRODS objects). The responses are then cached.
    """

    # Internal methods to implement by subclass
    def _get_context_string(self):
        """This function should be implemented by subclasses. It should return
           a string that is used in keys to identify the subclass.

           :raises Exception: if function has not been implemented in subclass.
        """
        raise Exception("Context string not provided by CacheDataManager.")

    def _get_original_data(self, ctx, keyname):
        """This function is called when data needs to be retrieved from the original
           (non-cached) location.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key

           :raises Exception: if function has not been implemented in subclass.
        """
        raise Exception("Get original data not implemented by CacheDataManager,")

    def _put_original_data(self, ctx, keyname, data):
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

    def __init__(self, *args, **kwargs):
        try:
            self._connection = redis.Redis(host="localhost")
        except BaseException:
            print("Error: opening Redis ARB connection failed with exception: " + traceback.format_exc())
            self._connection = None

    def _get_connection(self):
        return self._connection

    def _cache_available(self):
        if self._connection is None:
            return False

        try:
            return self._connection.ping()
        except BaseException:
            return False

    def _get_cache_keyname(self, keyname):
        return self._get_context_string() + "::" + keyname

    def get(self, ctx, keyname):
        """Retrieves data from the cache if possible, otherwise retrieves
           the original.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key

           :returns:       data for this key
        """
        connection = self._get_connection()
        cache_keyname = self._get_cache_keyname(keyname)

        if self._cache_available():
            cached_result = connection.get(cache_keyname)
        else:
            cached_result = None

        if cached_result is None:
            original_result = self._get_original_data(ctx, keyname)
            if self._should_populate_cache_on_get() and self._cache_available():
                self._update_cache(ctx, keyname, original_result)
            return original_result
        else:
            return cached_result

    def put(self, ctx, keyname, data):
        """Update both the original value and cached value (if cache is not available, it is not updated)

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
           :param data: data for this key
        """
        self._put_original_data(ctx, keyname, data)
        if self._cache_available():
            self._update_cache(ctx, keyname, data)

    def _update_cache(self, ctx, keyname, data):
        """Update a value in the cache

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
           :param data: data for this key
        """
        cache_keyname = self._get_cache_keyname(keyname)
        self._get_connection().set(cache_keyname, data)

    def clear(self, ctx, keyname):
        """Clears cached data for a key if present.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
        """
        cache_keyname = self._get_cache_keyname(keyname)
        self._get_connection().delete(cache_keyname)

    def _should_populate_cache_on_get(self):
        """This function controls whether the manager populates the cache
           after retrieving original data.

           :returns: boolean value that determines whether the data manager populates
                     the cache after retrieving data
        """
        return False
