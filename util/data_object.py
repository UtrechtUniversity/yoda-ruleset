# -*- coding: utf-8 -*-
"""Utility / convenience functions for data object IO."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import binascii
import json

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


def get_properties(ctx, data_id, resource):
    """ Retrieves default properties of a data object from iRODS.

    :param ctx:                                   Combined type of a callback and rei struct
    :param data_id:                               data_id of the data object
    :param resource:                              Name of resource

    :returns: dictionary mapping each requested property to its retrieved value, or None if not found.
    """
    # Default properties available for retrieva
    properties = [
        "DATA_ID", "DATA_MODIFY_TIME", "DATA_OWNER_NAME", "DATA_SIZE",
        "COLL_ID", "DATA_RESC_HIER", "DATA_NAME", "COLL_NAME",
    ]

    # Retrieve data obejct with default properties
    query_fields = ", ".join(properties)
    iter = genquery.row_iterator(
        query_fields,
        "DATA_ID = '{}' AND DATA_RESC_HIER like '{}%'".format(data_id, resource),
        genquery.AS_LIST, ctx
    )

    # Return a None when no data object is found
    prop_dict = None

    for row in iter:
        prop_dict = {prop: value for prop, value in zip(properties, row)}
        break

    return prop_dict


def owner(ctx, path):
    """Find the owner of a data object. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "DATA_OWNER_NAME, DATA_OWNER_ZONE",
                  "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
                  genquery.AS_LIST, ctx))
    return tuple(owners[0]) if len(owners) > 0 else None


def size(ctx, path):
    """Get a data object's size in bytes.

    :param ctx:      Combined type of a callback and rei struct
    :param path:     Path to iRODS data object

    :returns: Data object's size or None if object is not found
    """

    iter = genquery.row_iterator(
        "DATA_SIZE, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return int(row[0])


def has_replica_with_status(ctx, path, statuses):
    """Check if data object has replica with specified replica statuses.

    :param ctx:      Combined type of a callback and rei struct
    :param path:     Path to iRODS data object
    :param statuses: List of replica status to check

    :returns: Boolean indicating if data object has replicas with specified replica statuses
    """
    iter = genquery.row_iterator(
        "DATA_REPL_STATUS",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if constants.replica_status(int(row[0])) in statuses:
            return True

    return False


def write(ctx, path, data):
    """Write a string to an iRODS data object.

    This will overwrite the data object if it exists.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to iRODS data object
    :param data: Data to write to data object
    """
    if exists(ctx, path):
        ret = msi.data_obj_open(ctx, 'openFlags=O_WRONLYO_TRUNC++++objPath=' + path, 0)
        handle = ret['arguments'][1]
    else:
        ret = msi.data_obj_create(ctx, path, '', 0)
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

    json_inp = {"logical_path": path_copy, "options": {"reference": path_org}}
    msi.touch(ctx, json.dumps(json_inp))


def remove(ctx, path, force=False):
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
    # Get the modified date of the data object
    ret = msi.obj_stat(ctx, path_org, irods_types.RodsObjStat())
    output = ret['arguments'][1]
    modify_time = int(str(output.modifyTime))

    msi.data_obj_rename(ctx,
                        path_org,
                        path_target,
                        '0',
                        irods_types.BytesBuf())

    json_inp = {"logical_path": path_target, "options": {"seconds_since_epoch": modify_time}}
    msi.touch(ctx, json.dumps(json_inp))


def name_from_id(ctx, data_id):
    """Get data object name from data object id.

    :param ctx:     Combined type of a callback and rei struct
    :param data_id: Data object id

    :returns: Data object name
    """
    x = genquery.Query(ctx, "COLL_NAME, DATA_NAME", "DATA_ID = '{}'".format(data_id)).first()
    if x is not None:
        return '/'.join(x)


def id_from_path(ctx, path):
    """Get data object id from data object path at its first appearance.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to iRODS data object

    :returns: Data object id
    """
    return genquery.Query(ctx, "DATA_ID",
                          "COLL_NAME = '%s' AND DATA_NAME = '%s'" % pathutil.chop(path)).first()


def decode_checksum(checksum):
    """Decode data object checksum.

    :param checksum: Base64 encoded SHA256 checksum

    :returns: Data object's SHA256 checksum
    """
    if checksum is None:
        return "0"
    else:
        return binascii.hexlify(binascii.a2b_base64(checksum[5:])).decode("UTF-8")


def get_group_owners(ctx, path):
    """Return list of groups of data object, each entry being name of the group and the zone."""
    parent, basename = pathutil.chop(path)
    groups = list(genquery.row_iterator(
        "USER_NAME, USER_ZONE",
        "COLL_NAME = '{}' and DATA_NAME = '{}' AND USER_TYPE = 'rodsgroup' AND DATA_ACCESS_NAME = 'own'".format(parent, basename),
        genquery.AS_LIST, ctx
    ))
    return groups
