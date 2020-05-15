# -*- coding: utf-8 -*-
"""Utility / convenience functions for data object IO."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import msi
import pathutil
import genquery
import irods_types
import constants
from query import Query


def exists(callback, path):
    """Check if a data object with the given path exists"""
    return len(list(genquery.row_iterator(
               "DATA_ID",
               "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
               genquery.AS_LIST, callback))) > 0


def owner(callback, path):
    """Find the owner of a data object. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "DATA_OWNER_NAME, DATA_OWNER_ZONE",
                  "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
                  genquery.AS_LIST, callback))
    return tuple(owners[0]) if len(owners) > 0 else None


def size(callback, path):
    """Get a data object's size in bytes."""
    iter = genquery.row_iterator(
        "DATA_SIZE, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
        genquery.AS_LIST, callback
    )

    for row in iter:
        return int(row[0])
    else:
        return -1


def write(callback, path, data):
    """Write a string to an iRODS data object.
       This will overwrite the data object if it exists.
    """

    ret = msi.data_obj_create(callback, path, 'forceFlag=', 0)
    handle = ret['arguments'][2]

    ret = msi.data_obj_write(callback, handle, data, 0)
    msi.data_obj_close(callback, handle, 0)


def read(callback, path, max_size=constants.IIDATA_MAX_SLURP_SIZE):
    """Read an entire iRODS data object into a string."""

    sz = size(callback, path)
    if sz > max_size:
        raise UUFileSizeException('data_object.read: file size limit exceeded ({} > {})'
                                  .format(sz, max_size))

    if sz == 0:
        # Don't bother reading an empty file.
        return ''

    ret = msi.data_obj_open(callback, 'objPath=' + path, 0)
    handle = ret['arguments'][1]

    ret = msi.data_obj_read(callback,
                            handle,
                            sz,
                            irods_types.BytesBuf())

    buf = ret['arguments'][2]

    msi.data_obj_close(callback, handle, 0)

    return ''.join(buf.buf[:buf.len])


def copy(ctx, path_org, path_copy, force=True):
    """Copy a data object.

    :param path_org: Data object original path
    :param path_copy: Data object copy path
    :param force: applies "forceFlag"

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_copy(ctx,
                      path_org,
                      path_copy,
                      'verifyChksum={}'.format('++++forceFlag=' if force else ''),
                      irods_types.BytesBuf())


def remove(ctx, path, force=True):
    """Delete a data object.

    :param path: data object path
    :param force: applies "forceFlag"

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_unlink(ctx,
                        'objPath={}{}'.format(path, '++++forceFlag=' if force else ''),
                        irods_types.BytesBuf())


def rename(ctx, path_org, path_target):
    """Rename data object from path_org to path_target.

    :param path_org: Data object original path
    :param path_target: Data object new path

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_rename(ctx,
                        path_org,
                        path_target,
                        '0',
                        irods_types.BytesBuf())


def name_from_id(ctx, data_id):
    x = Query(ctx, "COLL_NAME, DATA_NAME", "DATA_ID = '{}'".format(data_id)).first()
    if x is not None:
        return '/'.join(x)
