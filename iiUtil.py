# \file      iiUtil.py
# \brief     Commonly used utility functions
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Utility / convenience functions for data object IO and collections. {{{

import json
import irods_types


def write_data_object(callback, path, data):
    """Write a string to an iRODS data object.
       This will overwrite the data object if it exists.
    """

    ret = data_obj_create(callback, path, 'forceFlag=', 0)
    handle = ret['arguments'][2]

    ret = data_obj_write(callback, handle, data, 0)
    data_obj_close(callback, handle, 0)


def read_data_object(callback, path, max_size=IIDATA_MAX_SLURP_SIZE):
    """Read an entire iRODS data object into a string."""

    data_size = getDataObjSize(callback, *chop_path(path))
    if data_size > max_size:
        raise UUFileSizeException('read_data_object: file size limit exceeded ({} > {})'
                                  .format(data_size, max_size))

    if data_size == 0:
        # Don't bother reading an empty file.
        return ''

    ret = data_obj_open(callback, 'objPath=' + path, 0)
    handle = ret['arguments'][1]

    ret = data_obj_read(callback,
                        handle,
                        data_size,
                        irods_types.BytesBuf())

    buf = ret['arguments'][2]

    data_obj_close(callback, handle, 0)

    return ''.join(buf.buf[0:buf.len])


def chop_path(path):
    """Split off the rightmost path component of a path
       /a/b/c -> (/a/b, c)
    """
    if path == '/' or len(path) == 0:
        return '/', ''
    else:
        x = path.split('/')
        return '/'.join(x[:-1]), x[-1]


# FIXME: All python queries need to deal with escaping e.g. ' and %.
def data_object_exists(callback, path):
    """Check if a data object with the given path exists"""
    return len(list(genquery.row_iterator(
               "DATA_ID",
               "COLL_NAME = '%s' AND DATA_NAME = '%s'" % chop_path(path),
               genquery.AS_LIST, callback))) > 0


def collection_exists(callback, path):
    """Check if a collection with the given path exists"""
    return len(list(genquery.row_iterator(
               "COLL_ID", "COLL_NAME = '%s'" % path,
               genquery.AS_LIST, callback))) > 0


def data_owner(callback, path):
    """Find the owner of a data object. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "DATA_OWNER_NAME, DATA_OWNER_ZONE",
                  "COLL_NAME = '%s' AND DATA_NAME = '%s'" % chop_path(path),
                  genquery.AS_LIST, callback))
    return tuple(owners[0]) if len(owners) > 0 else None


def collection_owner(callback, path):
    """Find the owner of a collection. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "COLL_OWNER_NAME, COLL_OWNER_ZONE",
                  "COLL_NAME = '%s'" % path,
                  genquery.AS_LIST, callback))
    return tuple(owners[0]) if len(owners) > 0 else None


def collection_empty(callback, path):
    """Check if a collection contains any data objects"""
    return (len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME = '{}'".format(path),
                     genquery.AS_LIST, callback))) == 0
        and len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME like '{}/%'".format(path),
                     genquery.AS_LIST, callback))) == 0)
# }}}


# Utility / convenience functions for dealing with JSON. {{{
class UUJsonException(UUException):
    """Exception for unparsable JSON text"""
    # Python2's JSON lib raises ValueError on bad parses, which is ambiguous.
    # Use this exception (together with the functions below) instead.
    # (this can also ease transitions to python3, since python3's json already
    # uses a different, unambiguous exception type: json.JSONDecodeError)


def parse_json(text):
    try:
        return json.loads(text)
    except ValueError:
        raise UUJsonException('JSON file format error')


def read_json_object(callback, path):
    """Read an iRODS data object and parse it as JSON."""
    return parse_json(read_data_object(callback, path))
# }}}


def get_client_name_zone(rei):
    """Obtain client name and zone, as a tuple"""
    client = session_vars.get_map(rei)['client_user']
    return client['user_name'], client['irods_zone']


def get_client_full_name(rei):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return '{}#{}'.format(*get_client_name_zone(rei))
