# -*- coding: utf-8 -*-
"""Utility / convenience functions for data object IO."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import irods_types

import constants
import error
import msi
import pathutil


def exists(ctx, path):
    """Check if a data object with the given path exists."""
    return len(list(genquery.row_iterator(
               "DATA_ID",
               "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
               genquery.AS_LIST, ctx))) > 0


def owner(ctx, path):
    """Find the owner of a data object. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "DATA_OWNER_NAME, DATA_OWNER_ZONE",
                  "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
                  genquery.AS_LIST, ctx))
    return tuple(owners[0]) if len(owners) > 0 else None


def size(ctx, path):
    """Get a data object's size in bytes."""
    iter = genquery.row_iterator(
        "DATA_SIZE, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return int(row[0])


def write(ctx, path, data):
    """Write a string to an iRODS data object.

    This will overwrite the data object if it exists.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to iRODS data object
    :param data: Data to write to data object
    """
    ret = msi.data_obj_create(ctx, path, 'forceFlag=', 0)
    handle = ret['arguments'][2]

    msi.data_obj_write(ctx, handle, data, 0)
    msi.data_obj_close(ctx, handle, 0)


def read(ctx, path, max_size=constants.IIDATA_MAX_SLURP_SIZE):
    """Read an entire iRODS data object into a string."""
    sz = size(ctx, path)
    if sz is None:
        raise error.UUFileNotExistError('data_object.read: object does not exist ({})'
                                        .format(path))

    if sz > max_size:
        raise error.UUFileSizeError('data_object.read: file size limit exceeded ({} > {})'
                                    .format(sz, max_size))

    if sz == 0:
        # Don't bother reading an empty file.
        return ''

    ret = msi.data_obj_open(ctx, 'objPath=' + path, 0)
    handle = ret['arguments'][1]

    ret = msi.data_obj_read(ctx,
                            handle,
                            sz,
                            irods_types.BytesBuf())

    buf = ret['arguments'][2]

    msi.data_obj_close(ctx, handle, 0)

    return ''.join(buf.buf[:buf.len])


def copy(ctx, path_org, path_copy, force=True):
    """Copy a data object.

    :param ctx:       Combined type of a callback and rei struct
    :param path_org:  Data object original path
    :param path_copy: Data object copy path
    :param force:     Applies "forceFlag"

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_copy(ctx,
                      path_org,
                      path_copy,
                      'numThreads=1++++verifyChksum={}'.format('++++forceFlag=' if force else ''),
                      irods_types.BytesBuf())


def remove(ctx, path, force=True):
    """Delete a data object.

    :param ctx:   Combined type of a callback and rei struct
    :param path:  Data object path
    :param force: Applies "forceFlag"

    This may raise a error.UUError if the file does not exist, or when the user
    does not have write permission.
    """
    msi.data_obj_unlink(ctx,
                        'objPath={}{}'.format(path, '++++forceFlag=' if force else ''),
                        irods_types.BytesBuf())


def rename(ctx, path_org, path_target):
    """Rename data object from path_org to path_target.

    :param ctx:         Combined type of a callback and rei struct
    :param path_org:    Data object original path
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
    """Get data object name from data object id.

    :param ctx:     Combined type of a callback and rei struct
    :param data_id: Data object id

    :returns: Data object name
    """
    x = genquery.Query(ctx, "COLL_NAME, DATA_NAME", "DATA_ID = '{}'".format(data_id)).first()
    if x is not None:
        return '/'.join(x)
