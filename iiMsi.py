# \file      iiMsi.py
# \brief     Python wrappers for iRODS microservices with error handling
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import irods_types


class UUException(Exception):
    """Generic Python rule exception"""


class UUFileSizeException(UUException):
    """File size limit exceeded"""

# Microservices may fail and indicate failure in a number of different ways.
# With this module, we aim to unify microservice error handling by converting
# all errors to unambiguous Python exceptions.

# Machinery for wrapping microservices and creating microservice-specific exceptions. {{{


class UUMsiException(UUException):
    """Exception for microservice failure"""

    def __init__(self, message, msi_status, msi_code, msi_args, src_exception):
        super(UUMsiException, self).__init__(message)
        # Store msi result, if any.
        # These may be None when an msi aborts in an abnormal way.
        self.msi_status = msi_status
        self.msi_code = msi_code
        self.msi_args = msi_args
        self.src_exception = src_exception

    def __str__(self):
        if self.msi_status is not None:
            return '{}: error code {}'.format(self.message, self.msi_code)
        elif self.src_exception is not None:
            return '{}: iRODS error <{}>'.format(self.message, self.src_exception)
        else:
            return self.message


def make_msi_exception(name, message):
    """Create a UUMsiException subtype for a specific microservice"""

    t = type('UUMsi{}Exception'.format(name), (UUMsiException,), {})
    t.__init__ = lambda self, status, code, args, e = None: \
        super(t, self).__init__(message, status, code, args, e)
    return t


def run_msi(msi, exception, *args):
    """Run an MSI such that it throws an MSI-specific exception on failure."""
    try:
        ret = msi(*args)
    except RuntimeError as e:
        # msi failures may be raised as non-specific RuntimeErrors.
        # There is no result to save, but we can still convert this to a
        # msi-specific exception.
        raise exception(None, None, None, e)

    if not ret['status']:
        # False status indicates error.
        raise exception(ret['status'],
                        ret['code'],
                        ret['arguments'])
    return ret


def wrap_msi(msi, exception):
    """Wrap an MSI such that it throws an MSI-specific exception on failure.
       The arguments to the wrapper are the same as that of the msi, only with
       a callback in front.

       e.g.:    callback.msiDataObjCreate(x, y, z)
       becomes: data_obj_create(callback, x, y, z)
    """
    return lambda callback, *args: run_msi(getattr(callback, msi), exception, *args)


def make_msi(name, error_text):
    """Creates msi wrapper function and exception type as a tuple.
       (see functions above)
    """
    e = make_msi_exception(name, error_text)
    return (wrap_msi('msi' + name, e), e)


# }}}
# Microservice wrappers {{{

# This naming scheme follows the original msi name, changed to snake_case and
# with the msi prefix removed.

data_obj_create, UUMsiDataObjCreateException = make_msi('DataObjCreate', 'Could not create data object')
data_obj_open,   UUMsiDataObjOpenException   = make_msi('DataObjOpen',   'Could not open data object')
data_obj_read,   UUMsiDataObjReadException   = make_msi('DataObjRead',   'Could not read data object')
data_obj_write,  UUMsiDataObjWriteException  = make_msi('DataObjWrite',  'Could not write data object')
data_obj_close,  UUMsiDataObjCloseException  = make_msi('DataObjClose',  'Could not close data object')
data_obj_copy,   UUMsiDataObjCopyException   = make_msi('DataObjCopy',   'Could not copy data object')
data_obj_unlink, UUMsiDataObjUnlinkException = make_msi('DataObjUnlink', 'Could not remove data object')
coll_create,     UUMsiCollCreateException    = make_msi('CollCreate',    'Could not create collection')
rm_coll,         UUMsiRmCollException        = make_msi('RmColl',        'Could not remove collection')
check_access,    UUMsiCheckAccessException   = make_msi('CheckAccess',   'Could not check access')
set_acl,         UUMsiSetACLException        = make_msi('SetACL',        'Could not set ACL')
get_icat_time,   UUMsiGetIcatTimeException   = make_msi('GetIcatTime',   'Could not get Icat time')

string_2_key_val_pair, UUMsiString2KeyValPairException = \
    make_msi('String2KeyValPair', 'Could not create keyval pair')

set_key_value_pairs_to_obj, UUMsiSetKeyValuePairsToObjException = \
    make_msi('SetKeyValuePairsToObj', 'Could not set metadata on object')

associate_key_value_pairs_to_obj, UUMsiAssociateKeyValuePairsToObjException = \
    make_msi('AssociateKeyValuePairsToObj', 'Could not associate metadata to object')

# Add new msis here as needed.

# }}}
