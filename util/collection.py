"""Utility / convenience functions for dealing with collections."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json
from functools import reduce
from typing import Iterable, List, Tuple

import genquery
import irods_types

import data_object
import msi
import rule


def exists(ctx: rule.Context, path: str) -> bool:
    """Check if a collection with the given path exists."""
    return len(list(genquery.row_iterator(
               "COLL_ID", "COLL_NAME = '{}'".format(path),
               genquery.AS_LIST, ctx))) > 0


def owner(ctx: rule.Context, path: str) -> Tuple[str, str] | None:
    """Find the owner of a collection. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "COLL_OWNER_NAME, COLL_OWNER_ZONE",
                  "COLL_NAME = '{}'".format(path),
                  genquery.AS_LIST, ctx))
    return tuple(owners[0]) if len(owners) > 0 else None


def is_empty(ctx: rule.Context, path: str) -> bool:
    """Check if a collection contains any data objects."""
    return (len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME = '{}'".format(path),
                     genquery.AS_LIST, ctx))) == 0
            and len(list(genquery.row_iterator(
                    "DATA_ID",
                    "COLL_NAME like '{}/%'".format(path),
                    genquery.AS_LIST, ctx))) == 0)


def size(ctx: rule.Context, path: str) -> int:
    """Get a collection's size in bytes."""
    def func(x: int, row: List) -> int:
        return x + int(row[1])

    return reduce(func,
                  itertools.chain(genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}'".format(path),
                                                        genquery.AS_LIST, ctx),
                                  genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}/%'".format(path),
                                                        genquery.AS_LIST, ctx)), 0)


def data_count(ctx: rule.Context, path: str, recursive: bool = True) -> int:
    """Get a collection's data count.

    :param ctx:       Combined type of a callback and rei struct
    :param path:      A collection path
    :param recursive: Measure subcollections as well

    :returns: Number of data objects
    """
    # Generators can't be fed to len(), so here we are...
    return sum(1 for _ in data_objects(ctx, path, recursive=recursive))


def collection_count(ctx: rule.Context, path: str, recursive: bool = True) -> int:
    """Get a collection's collection count (the amount of collections within a collection)."""
    return sum(1 for _ in genquery.row_iterator(
               "COLL_ID",
               "COLL_NAME like '{}/%'".format(path) if recursive else
               "COLL_PARENT_NAME = '{}' AND COLL_NAME like '{}/%'".format(path, path),
               genquery.AS_LIST, ctx))


def subcollections(ctx: rule.Context, path: str, recursive: bool = False) -> Iterable:
    """Get a list of all subcollections in a collection.

    Note: the returned value is a generator / lazy list, so that large
          collections can be handled without keeping everything in memory.
          use list(...) on the result to get an actual list if necessary.

    The returned paths are absolute paths (e.g. ['/tempZone/home/x']).

    :param ctx:       Combined type of a callback and rei struct
    :param path:      Path of collection
    :param recursive: List subcollections recursively

    :returns: List of all subcollections in a collection
    """

    q_root = genquery.row_iterator("COLL_NAME",
                                   "COLL_PARENT_NAME = '{}'".format(path),
                                   genquery.AS_LIST, ctx)

    if not recursive:
        return (row[0] for row in q_root)

    # Recursive? Return a generator combining both queries.
    q_sub = genquery.row_iterator("COLL_NAME",
                                  "COLL_PARENT_NAME like '{}/%'".format(path),
                                  genquery.AS_LIST, ctx)

    return (row[0] for row in itertools.chain(q_root, q_sub))


def data_objects(ctx: rule.Context, path: str, recursive: bool = False) -> Iterable:
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
    def to_absolute(row: List) -> str:
        return '{}/{}'.format(*row)

    q_root = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                   "COLL_NAME = '{}'".format(path),
                                   genquery.AS_LIST, ctx)

    if not recursive:
        return map(to_absolute, q_root)

    # Recursive? Return a generator combining both queries.
    q_sub = genquery.row_iterator("COLL_NAME, DATA_NAME",
                                  "COLL_NAME like '{}/%'".format(path),
                                  genquery.AS_LIST, ctx)

    return map(to_absolute, itertools.chain(q_root, q_sub))


def create(ctx: rule.Context, path: str, entire_tree: str = '') -> None:
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


def copy(ctx: rule.Context, path_org: str, path_copy: str, force: bool = True) -> None:
    """Copy a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param path_org:  Collection original path
    :param path_copy: Collection copy path
    :param force:     Applies "forceFlag"

    This may raise a error.UUError if the collection does not exist, or when
    the user does not have write permission.
    """
    if not force:
        create(ctx, path_copy)

    for row in genquery.row_iterator("DATA_NAME",
                                     "COLL_NAME = '{}'".format(path_org),
                                     genquery.AS_LIST,
                                     ctx):
        data_obj = row[0]
        data_object.copy(ctx,
                         path_org + "/" + data_obj,
                         path_copy + "/" + data_obj,
                         force)

    for row in genquery.row_iterator("COLL_NAME",
                                     "COLL_PARENT_NAME = '{}'".format(path_org),
                                     genquery.AS_LIST,
                                     ctx):
        coll = row[0]
        copy(ctx, coll, path_copy + coll[len(path_org):], force)

    json_inp = {"logical_path": path_copy, "options": {"reference": path_org}}
    msi.touch(ctx, json.dumps(json_inp))


def move(ctx: rule.Context, path_org: str, path_move: str, force: bool = True) -> None:
    """Move a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param path_org:  Collection original path
    :param path_move: Collection move path
    :param force:     Applies "forceFlag"

    This may raise a error.UUError if the collection does not exist, or when
    the user does not have write permission.
    """
    copy(ctx, path_org, path_move, force)
    msi.rm_coll(ctx,
                path_org,
                '',
                irods_types.BytesBuf())


def remove(ctx: rule.Context, path: str, force: bool = False) -> None:
    """Delete a collection.

    :param ctx:   Combined type of a callback and rei struct
    :param path:  Path of collection to be deleted
    :param force: Applies "forceFlag"

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.rm_coll(ctx,
                path,
                'forceFlag=' if force else '',
                irods_types.BytesBuf())


def rename(ctx: rule.Context, path_org: str, path_target: str) -> None:
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


def id_from_name(ctx: rule.Context, coll_name: str) -> str:
    """Get collection id from collection name.

    :param ctx:       Combined type of a callback and rei struct
    :param coll_name: Collection name

    :returns: Collection id
    """
    return genquery.Query(ctx, "COLL_ID", "COLL_NAME = '{}'".format(coll_name)).first()


def name_from_id(ctx: rule.Context, coll_id: str) -> str:
    """Get collection name from collection id.

    :param ctx:     Combined type of a callback and rei struct
    :param coll_id: Collection id

    :returns: Collection name
    """
    return genquery.Query(ctx, "COLL_NAME", "COLL_ID = '{}'".format(coll_id)).first()
