# \file      iiUtil.py
# \brief     Commonly used utility functions
# \author    Chris Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import irods_types
from collections import OrderedDict


# Utility / convenience functions for data object IO and collections. {{{

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

    size = data_size(callback, path)
    if size > max_size:
        raise UUFileSizeException('read_data_object: file size limit exceeded ({} > {})'
                                  .format(size, max_size))

    if size == 0:
        # Don't bother reading an empty file.
        return ''

    ret = data_obj_open(callback, 'objPath=' + path, 0)
    handle = ret['arguments'][1]

    ret = data_obj_read(callback,
                        handle,
                        size,
                        irods_types.BytesBuf())

    buf = ret['arguments'][2]

    data_obj_close(callback, handle, 0)

    return ''.join(buf.buf[:buf.len])


def chop_path(path):
    """Split off the rightmost path component of a path
       /a/b/c -> (/a/b, c)
    """
    # In practice, this is the same as os.path.split on POSIX systems,
    # but it's better to not rely on OS-defined path syntax for iRODS paths.
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


def data_owner(callback, path):
    """Find the owner of a data object. Returns (name, zone) or None."""
    owners = list(genquery.row_iterator(
                  "DATA_OWNER_NAME, DATA_OWNER_ZONE",
                  "COLL_NAME = '%s' AND DATA_NAME = '%s'" % chop_path(path),
                  genquery.AS_LIST, callback))
    return tuple(owners[0]) if len(owners) > 0 else None


def data_size(callback, path):
    """Get a data object's size in bytes."""
    iter = genquery.row_iterator(
        "DATA_SIZE, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % chop_path(path),
        genquery.AS_LIST, callback
    )

    for row in iter:
        return int(row[0])
    else:
        return -1


def collection_exists(callback, path):
    """Check if a collection with the given path exists"""
    return len(list(genquery.row_iterator(
               "COLL_ID", "COLL_NAME = '%s'" % path,
               genquery.AS_LIST, callback))) > 0


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


def collection_size(callback, path):
    """Get a collection's size in bytes."""
    size = 0

    iter = genquery.row_iterator(
        "DATA_ID, DATA_SIZE",
        "COLL_NAME like '{}'".format(path),
        genquery.AS_LIST, callback
    )
    for row in iter:
        size = size + int(row[1])

    iter = genquery.row_iterator(
        "DATA_ID, DATA_SIZE",
        "COLL_NAME like '{}/%'".format(path),
        genquery.AS_LIST, callback
    )
    for row in iter:
        size = size + int(row[1])

    return size


def collection_data_count(callback, path):
    """Get a collection's data count."""
    return (len(list(genquery.row_iterator(
                     "DATA_ID",
                     "COLL_NAME = '{}'".format(path),
                     genquery.AS_LIST, callback)))
            + len(list(genquery.row_iterator(
                    "DATA_ID",
                    "COLL_NAME like '{}/%'".format(path),
                    genquery.AS_LIST, callback))))



def collection_collection_count(callback, path):
    """Get a collection's collection count."""
    return (len(list(genquery.row_iterator(
                     "COLL_ID",
                     "COLL_NAME like '{}/%'".format(path),
                     genquery.AS_LIST, callback))))

# }}}


# Utility / convenience functions for dealing with JSON. {{{
class UUJsonException(UUException):
    """Exception for unparsable JSON text"""
    # Python2's JSON lib raises ValueError on bad parses, which is ambiguous.
    # Use this exception (together with the functions below) instead.
    # (this can also ease transitions to python3, since python3's json already
    # uses a different, unambiguous exception type: json.JSONDecodeError)


def parse_json(text):
    """Parse JSON into an OrderedDict."""
    try:
        return json.loads(text, object_pairs_hook=OrderedDict)
    except ValueError:
        raise UUJsonException('JSON file format error')


def read_json_object(callback, path):
    """Read an iRODS data object and parse it as JSON."""
    return parse_json(read_data_object(callback, path))


def write_json_object(callback, path, data):
    """Write a JSON object to an iRODS data object."""
    return write_data_object(callback, path, json.dumps(data, indent=4))

# }}}


# Dealing with users {{{

def get_client_name_zone(rei):
    """Obtain client name and zone, as a tuple"""
    client = session_vars.get_map(rei)['client_user']
    return client['user_name'], client['irods_zone']


def get_client_full_name(rei):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return '{}#{}'.format(*get_client_name_zone(rei))


def user_name_from_id(callback, user_id):
    """Retrieve username from user ID.

       Arguments:
       user_id -- User id

       Return:
       string -- User name
    """
    user_name = ""

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_ID = '%s'" % (str(user_id)),
        genquery.AS_LIST, callback
    )

    for row in iter:
        user_name = row[0]

    return user_name

# }}}
