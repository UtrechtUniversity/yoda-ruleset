# \file      iiMsi.py
# \brief     Python wrappers for iRODS microservices with error handling
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import irods_types


class UUException(Exception):
    """Generic Python rule exception"""

# Microservices may fail and indicate failure in a number of different ways.
# With this module, we aim to unify microservice error handling by converting
# all errors to unambiguous Python exceptions.

# Machinery for wrapping microservices and creating microservice-specific exceptions. {{{


class UUMsiException(UUException):
    """Exception for microservice failure"""

    def __init__(self, message, msi_status, msi_code, msi_args):
        super(UUMsiException, self).__init__(message)
        # Store msi result, if any.
        # These may be None when an msi aborts in an abnormal way.
        self.msi_status = msi_status
        self.msi_code   = msi_code
        self.msi_args   = msi_args

def make_msi_exception(name, message):
    """Create a UUMsiException subtype for a specific microservice"""

    t = type('UUMsi{}Exception'.format(name), (UUMsiException,), {})
    t.__init__ = lambda self, status, code, args: \
        super(t, self).__init__(message, status, code, args)
    return t


def run_msi(msi, exception, *args):
    """Run an MSI such that it throws an MSI-specific exception on failure."""
    try:
        ret = msi(*args)
    except RuntimeError as e:
        # msi failures may be raised as non-specific RuntimeErrors.
        # There is no result to save, but we can still convert this to a
        # msi-specific exception.
        raise exception(None, None, None)

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

# }}}
# Microservice wrappers for data object IO. {{{

UUMsiDataObjCreateException = make_msi_exception('DataObjCreate', 'Could not create data object')
UUMsiDataObjOpenException   = make_msi_exception('DataObjOpen',   'Could not open data object')
UUMsiDataObjReadException   = make_msi_exception('DataObjRead',   'Could not read data object')
UUMsiDataObjWriteException  = make_msi_exception('DataObjWrite',  'Could not write data object')
UUMsiDataObjCloseException  = make_msi_exception('DataObjClose',  'Could not close data object')

data_obj_create = wrap_msi('msiDataObjCreate', UUMsiDataObjCreateException)
data_obj_open   = wrap_msi('msiDataObjOpen',   UUMsiDataObjOpenException)
data_obj_read   = wrap_msi('msiDataObjRead',   UUMsiDataObjReadException)
data_obj_write  = wrap_msi('msiDataObjWrite',  UUMsiDataObjWriteException)
data_obj_close  = wrap_msi('msiDataObjClose',  UUMsiDataObjCloseException)

# Add new msis here as needed.

# }}}
