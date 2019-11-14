# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with collections."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import itertools

def exists(callback, path):
    """Check if a collection with the given path exists"""
    return len(list(genquery.row_iterator(
               "COLL_ID", "COLL_NAME = '{}'".format(path),
               genquery.AS_LIST, callback))) > 0


def owner(callback, path):
    """Find the owner of a collection. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "COLL_OWNER_NAME, COLL_OWNER_ZONE",
                  "COLL_NAME = '{}'".format(path),
                  genquery.AS_LIST, callback))
    return tuple(owners[0]) if len(owners) > 0 else None


def empty(callback, path):
    """Check if a collection contains any data objects"""
    return (len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME = '{}'".format(path),
                     genquery.AS_LIST, callback))) == 0
            and len(list(genquery.row_iterator(
                    "DATA_ID",
                    "COLL_NAME like '{}/%'".format(path),
                    genquery.AS_LIST, callback))) == 0)


def size(callback, path):
    """Get a collection's size in bytes."""
    return reduce(lambda x, row: x + int(row[1]),
                  itertools.chain(genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}'".format(path),
                                                        genquery.AS_LIST, callback),
                                  genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}/%'".format(path),
                                                        genquery.AS_LIST, callback)), 0)


def data_count(callback, path, recursive=True):
    """Get a collection's data count.

    :param path: A collection path
    :param recursive: Measure subcollections as well
    :return: A number of data objects.
    """
    # Generators can't be fed to len(), so here we are...
    return sum(1 for _ in data_objects(callback, path, recursive=recursive))


def collection_count(callback, path):
    """Get a collection's collection count (the amount of collections within a collection)."""
    return sum(1 for _ in genquery.row_iterator(
                     "COLL_ID",
                     "COLL_NAME like '{}/%'".format(path),
                     genquery.AS_LIST, callback))


def data_objects(callback, path, recursive=False):
    """Get a list of all data objects in a collection.

    Note: the returned value is a generator / lazy list, so that large
          collections can be handled without keeping everything in memory.
          use list(...) on the result to get an actual list if necessary.

    The returned paths are absolute paths (e.g. ['/tempZone/home/x/y.txt']).
    """

    # coll+data name -> path
    to_absolute = lambda row: '{}/{}'.format(*row)

    q_root = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                   "COLL_NAME = '{}'".format(path),
                                   genquery.AS_LIST, callback)

    if not recursive:
        return itertools.imap(to_absolute, q_root)

    # Recursive? Return a generator combining both queries.
    q_sub = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                  "COLL_NAME like '{}/%'".format(path),
                                  genquery.AS_LIST, callback)

    return itertools.imap(to_absolute, itertools.chain(q_root, q_sub))
