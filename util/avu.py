"""Utility / convenience functions for dealing with AVUs."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json
from collections import namedtuple
from typing import Dict, Iterable, List, Tuple

import genquery

import log
import msi
import pathutil
import rule

Avu = namedtuple('Avu', list('avu'))
Avu.attr  = Avu.a
Avu.value = Avu.v
Avu.unit  = Avu.u


def of_data(ctx: rule.Context, path: str) -> Iterable[Avu]:
    """Get (a,v,u) triplets for a given data object."""
    return (Avu(*x) for x in genquery.Query(ctx, "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
                                                 "COLL_NAME = '{}' AND DATA_NAME = '{}'".format(*pathutil.chop(path))))


def of_coll(ctx: rule.Context, coll: str) -> Iterable[Avu]:
    """Get (a,v,u) triplets for a given collection."""
    return (Avu(*x) for x in genquery.Query(ctx, "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
                                                 "COLL_NAME = '{}'".format(coll)))


def get_attr_val_of_coll(ctx: rule.Context, coll: str, attr: str) -> Dict:
    """Get the value corresponding to an attr for a given collection."""
    iter = genquery.Query(
        ctx,
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = '{}' AND COLL_NAME = '{}'".format(attr, coll))

    for row in iter:
        return row
    raise ValueError("Attribute {} not found in AVUs of collection {}".format(attr, coll))


def inside_coll(ctx: rule.Context, path: str, recursive: bool = False) -> Iterable:
    """Get a list of all AVUs inside a collection with corresponding paths.

    Note: the returned value is a generator / lazy list, so that large
          collections can be handled without keeping everything in memory.
          use list(...) on the result to get an actual list if necessary.

    The returned paths are absolute paths (e.g. '/tempZone/home/x').

    :param ctx:       Combined type of a callback and rei struct
    :param path:      Path of collection
    :param recursive: List AVUs recursively

    :returns: List of all AVUs inside a collection with corresponding paths
    """
    # coll+name -> path
    def to_absolute(row: List, type: str) -> Tuple[str, str, str, str, str]:
        if type == "collection":
            return (row[1], type, row[2], row[3], row[4])
        else:
            return ('{}/{}'.format(row[0], row[1]), type, row[2], row[3], row[4])

    collection_root = genquery.row_iterator(
        "COLL_PARENT_NAME, COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
        "COLL_PARENT_NAME = '{}'".format(path),
        genquery.AS_LIST, ctx)
    collection_root = (to_absolute(x, "collection") for x in collection_root)

    data_objects_root = genquery.row_iterator(
        "COLL_NAME, DATA_NAME, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
        "COLL_NAME = '{}'".format(path),
        genquery.AS_LIST, ctx)
    data_objects_root = (to_absolute(x, "data_object") for x in data_objects_root)

    if not recursive:
        return itertools.chain(collection_root, data_objects_root)

    collection_sub = genquery.row_iterator(
        "COLL_PARENT_NAME, COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
        "COLL_PARENT_NAME like '{}/%'".format(path),
        genquery.AS_LIST, ctx)
    collection_sub = (to_absolute(x, "collection") for x in collection_sub)

    data_objects_sub = genquery.row_iterator(
        "COLL_NAME, DATA_NAME, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
        "COLL_NAME like '{}/%'".format(path),
        genquery.AS_LIST, ctx)
    data_objects_sub = (to_absolute(x, "data_object") for x in data_objects_sub)

    return itertools.chain(collection_root, data_objects_root, collection_sub, data_objects_sub)


def of_group(ctx: rule.Context, group: str) -> Iterable[Avu]:
    """Get (a,v,u) triplets for a given group."""
    return (Avu(*x) for x in genquery.Query(ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, META_USER_ATTR_UNITS",
                                                 "USER_NAME = '{}' AND USER_TYPE = 'rodsgroup'".format(group)))


def set_on_data(ctx: rule.Context, path: str, a: str, v: str) -> None:
    """Set key/value metadata on a data object."""
    msi.mod_avu_metadata(ctx, "-d", path, "set", a, v, "")


def set_on_coll(ctx: rule.Context, coll: str, a: str, v: str, catch: bool = False) -> bool | None:
    """Set key/value metadata on a collection. Optionally catch any exceptions that occur.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection to get paginated contents of
    :param a:     Attribute
    :param v:     Value
    :param catch: Whether to catch any exceptions that occur

    :returns: True if catch=True and no exceptions occurred during operation
    """
    if catch:
        return _set_on_coll_catch(ctx, coll, a, v)  # type: ignore[func-returns-value]

    _set_on_coll(ctx, coll, a, v)
    return True


def _set_on_coll(ctx: rule.Context, coll: str, a: str, v: str) -> None:
    msi.mod_avu_metadata(ctx, "-C", coll, "set", a, v, "")


def _set_on_coll_catch(ctx: rule.Context, coll: str, a: str, v: str) -> bool | None:
    """Set AVU, but catch exception."""
    try:
        _set_on_coll(ctx, coll, a, v)
    except Exception:
        log.write(ctx, "Failed to set AVU {} on coll {}".format(a, coll))
        return False

    return True


def set_on_resource(ctx: rule.Context, resource: str, a: str, v: str) -> None:
    """Set key/value metadata on a resource."""
    msi.mod_avu_metadata(ctx, "-R", resource, "set", a, v, "")


def associate_to_data(ctx: rule.Context, path: str, a: str, v: str, u: str = '') -> None:
    """Associate key/value metadata to a data object."""
    msi.mod_avu_metadata(ctx, "-d", path, "add", a, v, u)


def associate_to_coll(ctx: rule.Context, coll: str, a: str, v: str, u: str = '') -> None:
    """Associate key/value metadata on a collection."""
    msi.mod_avu_metadata(ctx, "-C", coll, "add", a, v, u)


def associate_to_group(ctx: rule.Context, group: str, a: str, v: str, u: str = '') -> None:
    """Associate key/value metadata on a group."""
    msi.mod_avu_metadata(ctx, "-u", group, "add", a, v, u)


def associate_to_resource(ctx: rule.Context, resource: str, a: str, v: str, u: str = '') -> None:
    """Associate key/value metadata on a group."""
    msi.mod_avu_metadata(ctx, "-R", resource, "add", a, v, u)


def rm_from_coll(ctx: rule.Context, coll: str, a: str, v: str) -> None:
    """Remove key/value metadata from a collection."""
    msi.mod_avu_metadata(ctx, "-C", coll, "rm", a, v, "")


def rm_from_data(ctx: rule.Context, path: str, a: str, v: str) -> None:
    """Remove key/value metadata from a data object."""
    msi.mod_avu_metadata(ctx, "-d", path, "rm", a, v, "")


def rm_from_group(ctx: rule.Context, group: str, a: str, v: str) -> None:
    """Remove key/value metadata from a group."""
    msi.mod_avu_metadata(ctx, "-u", group, "rm", a, v, "")


def wildcard_filter(avu: Tuple[str, str, str], a_filter: str, v_filter: str, u_filter: str) -> bool:
    """Wildcard filter for rmw operations."""
    a, v, u = avu

    def matches(value: str, filter_val: str) -> bool:
        if filter_val == "%":
            return True
        if filter_val.endswith("%"):
            prefix = filter_val[:-1]
            return value.startswith(prefix)
        return value == filter_val

    return matches(a, a_filter) and matches(v, v_filter) and matches(u, u_filter)


def rmw_from_coll(ctx: rule.Context, coll: str, a: str, v: str, u: str = '%', catch: bool = False) -> bool:
    """Remove AVU from collection with wildcards. Optionally catch any exceptions that occur.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection to operate on
    :param a:     Attribute pattern to match (supports wildcards)
    :param v:     Value pattern to match (supports wildcards)
    :param u:     Unit pattern to match (supports wildcards) (default: '%')
    :param catch: Whether to catch any exceptions that occur

    :returns: True if catch=True and no exceptions occurred during operation
    """
    if catch:
        return _rmw_from_coll_catch(ctx, coll, a, v, u)

    _rmw_from_coll(ctx, coll, a, v, u)
    return True


def _rmw_from_coll(ctx: rule.Context, coll: str, a: str, v: str, u: str) -> None:
    # Retrieve list of AVUs of collection.
    avus = [(avu.attr, avu.value, avu.unit) for avu in of_coll(ctx, coll)]

    # Filter list of AVUs.
    avus_filtered = [avu for avu in avus if wildcard_filter(avu, a, v, u)]

    # Remove filtered AVUs.
    for (a_, v_, u_) in avus_filtered:
        msi.mod_avu_metadata(ctx, "-C", coll, "rm", a_, v_, u_)


def _rmw_from_coll_catch(ctx: rule.Context, obj: str, a: str, v: str, u: str) -> bool:
    try:
        _rmw_from_coll(ctx, obj, a, v, u)
    except Exception:
        log.write(ctx, "Failed to rmw AVU {} on coll {}".format(a, obj))
        return False

    return True


def rmw_from_data(ctx: rule.Context, obj: str, a: str, v: str, u: str = '%') -> None:
    """Remove AVUs from data object with wildcards.

    :param ctx: Combined type of a callback and rei struct
    :param obj: Data object to operate on
    :param a:   Attribute pattern to match (supports wildcards)
    :param v:   Value pattern to match (supports wildcards)
    :param u:   Unit pattern to match (supports wildcards) (default: '%')
    """
    # Retrieve list of AVUs of data object.
    avus = [(avu.attr, avu.value, avu.unit) for avu in of_data(ctx, obj)]

    # Filter list of AVUs.
    avus_filtered = [avu for avu in avus if wildcard_filter(avu, a, v, u)]

    # Remove filtered AVUs.
    for (a_, v_, u_) in avus_filtered:
        msi.mod_avu_metadata(ctx, "-d", obj, "rm", a_, v_, u_)


def rmw_from_group(ctx: rule.Context, group: str, a: str, v: str, u: str = '%') -> None:
    """Remove AVUs from group with wildcards.

    :param ctx:   Combined type of a callback and rei struct
    :param group: Group to operate on
    :param a:     Attribute pattern to match (supports wildcards)
    :param v:     Value pattern to match (supports wildcards)
    :param u:     Unit pattern to match (supports wildcards) (default: '%')
    """
    # Retrieve list of AVUs of group.
    avus = [(avu.attr, avu.value, avu.unit) for avu in of_group(ctx, group)]

    # Filter list of AVUs.
    avus_filtered = [avu for avu in avus if wildcard_filter(avu, a, v, u)]

    # Remove filtered AVUs.
    for (a_, v_, u_) in avus_filtered:
        msi.mod_avu_metadata(ctx, "-u", group, "rm", a_, v_, u_)


def apply_atomic_operations(ctx: rule.Context, operations: Dict) -> bool:
    """Sequentially executes all operations as a single transaction.

    Operations should be a dict with structure as defined in
    https://docs.irods.org/4.2.12/doxygen/libmsi__atomic__apply__metadata__operations_8cpp.html
    If an error occurs, all updates are rolled back and an error is returned.

    :param ctx:        Combined type of a callback and rei struct
    :param operations: Dict containing the batch of metadata operations

    :returns: Boolean indicating if all metadata operations were executed
    """
    try:
        msi.atomic_apply_metadata_operations(ctx, json.dumps(operations), "")
        return True
    except msi.Error as e:
        # iRODS errorcode -1811000 (INVALID_OPERATION)
        if str(e).find("-1811000") > -1:
            log.write(ctx, "apply_atomic_operations: invalid metadata operation")
        # iRODS errorcode -130000 (SYS_INVALID_INPUT_PARAM)
        elif str(e).find("-130000") > -1:
            log.write(ctx, "apply_atomic_operations: invalid entity name or entity type")
        else:
            log.write(ctx, "apply_atomic_operations: {}".format(e))
        return False
