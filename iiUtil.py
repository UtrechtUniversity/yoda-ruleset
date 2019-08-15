# \file      iiUtil.py
# \brief     Commonly used utility functions
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Utility / convenience functions for data object IO. {{{


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
