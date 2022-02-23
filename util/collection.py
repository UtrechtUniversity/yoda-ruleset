# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with collections."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import sys
if sys.version_info > (2, 7):
    from functools import reduce

import genquery
import irods_types

import msi


def exists(ctx, path):
    """Check if a collection with the given path exists."""
    return len(list(genquery.row_iterator(
               "COLL_ID", "COLL_NAME = '{}'".format(path),
               genquery.AS_LIST, ctx))) > 0


def owner(ctx, path):
    """Find the owner of a collection. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "COLL_OWNER_NAME, COLL_OWNER_ZONE",
                  "COLL_NAME = '{}'".format(path),
                  genquery.AS_LIST, ctx))
    return tuple(owners[0]) if len(owners) > 0 else None


def empty(ctx, path):
    """Check if a collection contains any data objects."""
    return (len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME = '{}'".format(path),
                     genquery.AS_LIST, ctx))) == 0
            and len(list(genquery.row_iterator(
                    "DATA_ID",
                    "COLL_NAME like '{}/%'".format(path),
                    genquery.AS_LIST, ctx))) == 0)


def size(ctx, path):
    """Get a collection's size in bytes."""
    def func(x, row):
        return x + int(row[1])

    return reduce(func,
                  itertools.chain(genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}'".format(path),
                                                        genquery.AS_LIST, ctx),
                                  genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}/%'".format(path),
                                                        genquery.AS_LIST, ctx)), 0)


def data_count(ctx, path, recursive=True):
    """Get a collection's data count.

    :param ctx:       Combined type of a callback and rei struct
    :param path:      A collection path
    :param recursive: Measure subcollections as well

    :returns: Number of data objects
    """
    # Generators can't be fed to len(), so here we are...
    return sum(1 for _ in data_objects(ctx, path, recursive=recursive))


def collection_count(ctx, path, recursive=True):
    """Get a collection's collection count (the amount of collections within a collection)."""
    return sum(1 for _ in genquery.row_iterator(
               "COLL_ID",
               "COLL_NAME like '{}/%'".format(path) if recursive else
               "COLL_PARENT_NAME = '{}' AND COLL_NAME like '{}/%'".format(path, path),
               genquery.AS_LIST, ctx))


def data_objects(ctx, path, recursive=False):
    """Get a list of all data objects in a collection.

    Note: the returned value is a generator / lazy list, so that large
          collections can be handled without keeping everything in memory.
          use list(...) on the result to get an actual list if necessary.

    The returned paths are absolute paths (e.g. ['/tempZone/home/x/y.txt']).

    :param ctx:       Combined type of a callback and rei struct
    :param path:      Path of collection
    :param recursive: List data objects in subcollections recursively

    :returns: List of all data objects in a collection
    """
    # coll+data name -> path
    def to_absolute(row):
        return '{}/{}'.format(*row)

    q_root = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                   "COLL_NAME = '{}'".format(path),
                                   genquery.AS_LIST, ctx)

    if not recursive:
        return itertools.imap(to_absolute, q_root)

    # Recursive? Return a generator combining both queries.
    q_sub = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                  "COLL_NAME like '{}/%'".format(path),
                                  genquery.AS_LIST, ctx)

    return itertools.imap(to_absolute, itertools.chain(q_root, q_sub))


def create(ctx, path, entire_tree=''):
    """Create new collection.

    :param ctx:         Combined type of a callback and rei struct
    :param path:        Path including new collection
    :param entire_tree: Flag specifying parent collections will be created too

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.coll_create(ctx,
                    path,
                    entire_tree,
                    irods_types.BytesBuf())


def copy(ctx, path_org, path_copy):
    """Copy a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param path_org:  Collection original path
    :param path_copy: Collection copy path

    This may raise a error.UUError if the collection does not exist, or when
    the user does not have write permission.
    """
    msi.coll_rsync(ctx,
                   path_org,
                   path_copy,
                   '',
                   'IRODS_TO_IRODS',
                   irods_types.BytesBuf())


def move(ctx, path_org, path_move):
    """Move a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param path_org:  Collection original path
    :param path_move: Collection move path

    This may raise a error.UUError if the collection does not exist, or when
    the user does not have write permission.
    """
    msi.coll_rsync(ctx,
                   path_org,
                   path_move,
                   '',
                   'IRODS_TO_IRODS',
                   irods_types.BytesBuf())
    msi.rm_coll(ctx,
                path_org,
                '',
                irods_types.BytesBuf())


def remove(ctx, path):
    """Delete a collection.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of collection to be deleted

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.rm_coll(ctx,
                path,
                '',
                irods_types.BytesBuf())


def rename(ctx, path_org, path_target):
    """Rename collection from path_org to path_target.

    :param ctx:         Combined type of a callback and rei struct
    :param path_org:    Collection original path
    :param path_target: Collection new path

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_rename(ctx,
                        path_org,
                        path_target,
                        '1',
                        irods_types.BytesBuf())


def id_from_name(ctx, coll_name):
    """Get collection id from collection name.

    :param ctx:     Combined type of a callback and rei struct
    :param coll_name: Collection name

    :returns: Collection id
    """
    return genquery.Query(ctx, "COLL_ID", "COLL_NAME = '{}'".format(coll_name)).first()


def name_from_id(ctx, coll_id):
    """Get collection name from collection id.

    :param ctx:     Combined type of a callback and rei struct
    :param coll_id: Collection id

    :returns: Collection name
    """
    return genquery.Query(ctx, "COLL_NAME", "COLL_ID = '{}'".format(coll_id)).first()
