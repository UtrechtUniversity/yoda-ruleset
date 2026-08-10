"""Utility / convenience functions for dealing with collections."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from functools import reduce
from typing import Iterable, List, Tuple

import genquery
import irods_types
from tstrings import t

import data_object
import msi
import rule
from exceptions import *


def exists(ctx: rule.Context, path: str) -> bool:
    """Check if a collection with the given path exists.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A collection path

    :returns: Boolean indicating if collection exists
    """
    return len(list(genquery.Query(
                    ctx, "COLL_ID",
                    t("COLL_NAME = '{path}'"),
                    output=genquery.AS_LIST, limit=1, parser=genquery.Parser.GENQUERY2))) > 0


def owner(ctx: rule.Context, path: str) -> Tuple[str, str] | None:
    """Find the owner of a collection. Returns (name, zone) or None.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A collection path

    :returns: Owner of collection or None
    """
    owners = list(genquery.row_iterator(
                  "COLL_OWNER_NAME, COLL_OWNER_ZONE",
                  t("COLL_NAME = '{path}'"),
                  genquery.AS_LIST, ctx))
    return tuple(owners[0]) if len(owners) > 0 else None


def is_empty(ctx: rule.Context, path: str) -> bool:
    """Check if a collection contains any data objects.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A collection path

    :returns: Boolean indicating if collection is empty
    """
    return len(list(genquery.Query(
                    ctx, "DATA_ID",
                    t("COLL_NAME = '{path}' OR COLL_NAME like '{path}/%'"),
                    output=genquery.AS_LIST, parser=genquery.Parser.GENQUERY2))) == 0


def size(ctx: rule.Context, path: str) -> int:
    """Get a collection's size in bytes.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A collection path

    :returns: Collection size in bytes
    """
    def func(x: int, row: List) -> int:
        return x + int(row[1])

    return reduce(func, list(genquery.Query(
                             ctx, "distinct DATA_ID, DATA_SIZE",
                             t("COLL_NAME = '{path}' OR COLL_NAME like '{path}/%'"),
                             output=genquery.AS_LIST, parser=genquery.Parser.GENQUERY2)), 0)


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
    return sum(1 for _ in list(genquery.Query(
                               ctx, "distinct COLL_ID",
                               t("COLL_NAME like '{path}/%'") if recursive else
                               t("COLL_PARENT_NAME = '{path}' AND COLL_NAME like '{path}/%'"),
                               output=genquery.AS_LIST, parser=genquery.Parser.GENQUERY2)))


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
    return (row[0] for row in list(genquery.Query(
                                   ctx, "distinct COLL_NAME",
                                   t("COLL_PARENT_NAME = '{path}' OR COLL_PARENT_NAME like '{path}/%'") if recursive else
                                   t("COLL_PARENT_NAME = '{path}'"),
                                   output=genquery.AS_LIST, parser=genquery.Parser.GENQUERY2)))


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
        return f'{row[0]}/{row[1]}'

    return map(to_absolute, list(genquery.Query(
                                 ctx, "distinct COLL_NAME, DATA_NAME",
                                 t("COLL_NAME = '{path}' OR COLL_NAME like '{path}/%'") if recursive else
                                 t("COLL_NAME = '{path}'"),
                                 output=genquery.AS_LIST, parser=genquery.Parser.GENQUERY2)))


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
                                     t("COLL_NAME = '{path_org}'"),
                                     genquery.AS_LIST,
                                     ctx):
        data_obj = row[0]
        data_object.copy(ctx,
                         path_org + "/" + data_obj,
                         path_copy + "/" + data_obj,
                         force)

    for row in genquery.row_iterator("COLL_NAME",
                                     t("COLL_PARENT_NAME = '{path_org}'"),
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
                'forceFlag=' if force else '',
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


def empty(ctx: rule.Context, path: str) -> None:
    """Empty a collection (remove all data objects and subcollections).

    :param ctx:   Combined type of a callback and rei struct
    :param path:  Path of collection to be emptied
    """
    for row in genquery.row_iterator("DATA_NAME",
                                     t("COLL_NAME = '{path}'"),
                                     genquery.AS_LIST,
                                     ctx):
        data_object.remove(ctx, f"{path}/{row[0]}")

    for row in genquery.row_iterator("COLL_NAME",
                                     t("COLL_PARENT_NAME = '{path}'"),
                                     genquery.AS_LIST,
                                     ctx):
        remove(ctx, f"{path}/{row[0]}")


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
    return genquery.Query(ctx, "COLL_ID", t("COLL_NAME = '{coll_name}'")).first()


def name_from_id(ctx: rule.Context, coll_id: str) -> str:
    """Get collection name from collection id.

    :param ctx:     Combined type of a callback and rei struct
    :param coll_id: Collection id

    :returns: Collection name
    """
    return genquery.Query(ctx, "COLL_NAME", f"COLL_ID = '{coll_id}'").first()


def has_dataobjects(ctx: rule.Context, collection_name: str) -> bool:
    """Determines whether collection or any of its subcollections has any
       data objects

    :param ctx:             Combined type of a callback and rei struct
    :param collection_name: Collection name

    :raises CollectionNotFoundException: if collection has not been found

    :returns: Boolean value than indicates whether the collection or any of its
              subcollections has any data objects.
    """
    if not exists(ctx, collection_name):
        raise CollectionNotFoundException("Collection not found")

    where_clause = {
        'self': t("COLL_NAME = '{collection_name}'"),
        'subfolders': t("COLL_NAME LIKE '{collection_name}/%'")
    }

    for folder_type in ['self', 'subfolders']:
        iter_subcoll = genquery.row_iterator(
            "COUNT(DATA_NAME)",
            where_clause[folder_type],
            genquery.AS_LIST, ctx
        )
        # This loop should only run once
        for sub_row in iter_subcoll:
            if int(sub_row[0]) > 0:
                iter_subcoll.close()
                return True

    return False


def has_modify_date_after(ctx: rule.Context, collection_name: str, timestamp: int) -> bool:
    """Determines whether a collection has a collection modification date after a
       particular timestamp

    :param ctx:             Combined type of a callback and rei struct
    :param collection_name: Collection name
    :param timestamp:       Epoch time to compare modification time to

    :raises CollectionNotFoundException: if collection has not been found

    :returns: boolean value that indicates whether the collection has a more recent modification time
              than the provided timestamp.
    """
    iter_data = genquery.row_iterator(
        "COLL_MODIFY_TIME",
        t("COLL_NAME = '{collection_name}'"),
        genquery.AS_LIST, ctx
    )
    # This loop should only run once
    for sub_row in iter_data:
        return int(sub_row[0]) > timestamp

    raise CollectionNotFoundException("Collection not found")


def has_dataobjects_modified_after(ctx: rule.Context, collection_name: str, timestamp: int, fallback_to_collection_modified: bool = False) -> bool:
    """Determines whether a collection has data objects that have been modified
       after a particular timestamp.

    :param ctx:             Combined type of a callback and rei struct
    :param collection_name: Collection name
    :param timestamp:       Epoch time to compare modification time of data objects to
    :param fallback_to_collection_modified: If this is enabled, and the collection has no
                       data objects, compare the provided timestamp to the collection modification time
                       instead.

    :raises CollectionNotFoundException: if collection has not been found

    :returns: boolean value that indicates whether the collection has more recent modifications than the provided
              timestamp
    """
    if not exists(ctx, collection_name):
        raise CollectionNotFoundException("Collection not found")
    collections = [collection_name] + list(subcollections(ctx, collection_name, recursive=True))

    for _c in collections:
        # Get count of any data objects that have been modified after the inactivity cut off
        formatted_timestamp = f"{timestamp:011d}"  # noqa F841
        iter_recent_data = genquery.row_iterator(
            "COUNT(DATA_NAME)",
            t("COLL_NAME = '{_c}' AND DATA_MODIFY_TIME > '{formatted_timestamp}'"),
            genquery.AS_LIST, ctx
        )

        # This loop should only run once
        for count_row in iter_recent_data:
            if int(count_row[0]) > 0:
                iter_recent_data.close()
                return True

    if fallback_to_collection_modified and not has_dataobjects(ctx, collection_name):
        return has_modify_date_after(ctx, collection_name, timestamp)
    else:
        return False
