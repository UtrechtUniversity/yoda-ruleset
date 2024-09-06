# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with AVUs."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json
from collections import namedtuple

import genquery
import irods_types

import log
import msi
import pathutil

Avu = namedtuple('Avu', list('avu'))
Avu.attr  = Avu.a
Avu.value = Avu.v
Avu.unit  = Avu.u


def of_data(ctx, path):
    """Get (a,v,u) triplets for a given data object."""
    return itertools.imap(lambda x: Avu(*x),
                          genquery.Query(ctx, "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
                                              "COLL_NAME = '{}' AND DATA_NAME = '{}'".format(*pathutil.chop(path))))


def of_coll(ctx, coll):
    """Get (a,v,u) triplets for a given collection."""
    return itertools.imap(lambda x: Avu(*x),
                          genquery.Query(ctx, "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
                                              "COLL_NAME = '{}'".format(coll)))


def get_val_of_coll(ctx, coll, attr):
    """Get single value for a given collection given attribute name"""
    # TODO integration tests?
    iter = genquery.Query(ctx, "META_COLL_ATTR_VALUE",
                          "COLL_NAME = '{}' and META_COLL_ATTR_NAME = '{}'".format(coll, attr))

    for row in iter:
        return row

    return None


def inside_coll(ctx, path, recursive=False):
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
    def to_absolute(row, type):
        if type == "collection":
            return (row[1], type, row[2], row[3], row[4])
        else:
            return ('{}/{}'.format(row[0], row[1]), type, row[2], row[3], row[4])

    collection_root = genquery.row_iterator(
        "COLL_PARENT_NAME, COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
        "COLL_PARENT_NAME = '{}'".format(path),
        genquery.AS_LIST, ctx)
    collection_root = itertools.imap(lambda x: to_absolute(x, "collection"), collection_root)

    data_objects_root = genquery.row_iterator(
        "COLL_NAME, DATA_NAME, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
        "COLL_NAME = '{}'".format(path),
        genquery.AS_LIST, ctx)
    data_objects_root = itertools.imap(lambda x: to_absolute(x, "data_object"), data_objects_root)

    if not recursive:
        return itertools.chain(collection_root, data_objects_root)

    collection_sub = genquery.row_iterator(
        "COLL_PARENT_NAME, COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
        "COLL_PARENT_NAME like '{}/%'".format(path),
        genquery.AS_LIST, ctx)
    collection_sub = itertools.imap(lambda x: to_absolute(x, "collection"), collection_sub)

    data_objects_sub = genquery.row_iterator(
        "COLL_NAME, DATA_NAME, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
        "COLL_NAME like '{}/%'".format(path),
        genquery.AS_LIST, ctx)
    data_objects_sub = itertools.imap(lambda x: to_absolute(x, "data_object"), data_objects_sub)

    return itertools.chain(collection_root, data_objects_root, collection_sub, data_objects_sub)


def of_group(ctx, group):
    """Get (a,v,u) triplets for a given group."""
    return itertools.imap(lambda x: Avu(*x),
                          genquery.Query(ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, META_USER_ATTR_UNITS",
                                              "USER_NAME = '{}' AND USER_TYPE = 'rodsgroup'".format(group)))


def set_on_data(ctx, path, a, v):
    """Set key/value metadata on a data object."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.set_key_value_pairs_to_obj(ctx, x['arguments'][1], path, '-d')


def set_on_coll(ctx, coll, a, v, catch=False):
    """Set key/value metadata on a collection. Optionally catch any exceptions that occur.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection to get paginated contents of
    :param a:     Attribute
    :param v:     Value
    :param catch: Whether to catch any exceptions that occur

    :returns: True if catch=True and no exceptions occurred during operation
    """
    if catch:
        return _set_on_coll_catch(ctx, coll, a, v)

    _set_on_coll(ctx, coll, a, v)
    return True


def _set_on_coll(ctx, coll, a, v):
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.set_key_value_pairs_to_obj(ctx, x['arguments'][1], coll, '-C')


def _set_on_coll_catch(ctx, coll, a, v):
    """Set AVU, but catch exception."""
    try:
        _set_on_coll(ctx, coll, a, v)
    except Exception:
        log.write(ctx, "Failed to set AVU {} on coll {}".format(a, coll))
        return False

    return True


def set_on_resource(ctx, resource, a, v):
    """Set key/value metadata on a resource."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.set_key_value_pairs_to_obj(ctx, x['arguments'][1], resource, '-R')


def associate_to_data(ctx, path, a, v):
    """Associate key/value metadata to a data object."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.associate_key_value_pairs_to_obj(ctx, x['arguments'][1], path, '-d')


def associate_to_coll(ctx, coll, a, v):
    """Associate key/value metadata on a collection."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.associate_key_value_pairs_to_obj(ctx, x['arguments'][1], coll, '-C')


def associate_to_group(ctx, group, a, v):
    """Associate key/value metadata on a group."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.associate_key_value_pairs_to_obj(ctx, x['arguments'][1], group, '-u')


def associate_to_resource(ctx, resource, a, v):
    """Associate key/value metadata on a group."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.associate_key_value_pairs_to_obj(ctx, x['arguments'][1], resource, '-R')


def rm_from_coll(ctx, coll, a, v):
    """Remove key/value metadata from a collection."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.remove_key_value_pairs_from_obj(ctx, x['arguments'][1], coll, '-C')


def rm_from_data(ctx, coll, a, v):
    """Remove key/value metadata from a data object."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.remove_key_value_pairs_from_obj(ctx, x['arguments'][1], coll, '-d')


def rm_from_group(ctx, group, a, v):
    """Remove key/value metadata from a group."""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.remove_key_value_pairs_from_obj(ctx, x['arguments'][1], group, '-u')


def rmw_from_coll(ctx, obj, a, v, catch=False, u=''):
    """Remove AVU from collection with wildcards. Optionally catch any exceptions that occur.

    :param ctx:   Combined type of a callback and rei struct
    :param obj:  Collection to get paginated contents of
    :param a:     Attribute
    :param v:     Value
    :param catch: Whether to catch any exceptions that occur
    :param u:     Unit

    :returns: True if catch=True and no exceptions occurred during operation
    """
    if catch:
        return _rmw_from_coll_catch(ctx, obj, a, v, u)

    _rmw_from_coll(ctx, obj, a, v, u)
    return True


def _rmw_from_coll(ctx, obj, a, v, u=''):
    msi.rmw_avu(ctx, '-C', obj, a, v, u)


def _rmw_from_coll_catch(ctx, obj, a, v, u=''):
    try:
        _rmw_from_coll(ctx, obj, a, v, u)
    except Exception:
        log.write(ctx, "Failed to rm AVU {} on coll {}".format(a, obj))
        return False

    return True


def rmw_from_data(ctx, obj, a, v, u=''):
    """Remove AVU from data object with wildcards."""
    msi.rmw_avu(ctx, '-d', obj, a, v, u)


def rmw_from_group(ctx, group, a, v, u=''):
    """Remove AVU from group with wildcards."""
    msi.rmw_avu(ctx, '-u', group, a, v, u)


def apply_atomic_operations(ctx, operations):
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
