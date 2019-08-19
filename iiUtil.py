# \file      iiUtil.py
# \brief     Commonly used utility functions
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Utility / convenience functions for data object IO. {{{

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


def read_data_object(callback, path):
    """Read an entire iRODS data object into a string."""

    # Get file size.
    coll_name, data_name = os.path.split(path)
    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open, read, close.
    ret = data_obj_open(callback, 'objPath=' + path, 0)
    handle = ret['arguments'][1]

    ret = data_obj_read(callback, handle, data_size,
                        irods_types.BytesBuf())

    data_obj_close(callback, handle, 0)

    return ''.join(ret['arguments'][2].buf)

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
