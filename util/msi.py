# -*- coding: utf-8 -*-
"""iRODS microservice wrappers that provide primitive error handling

Microservices may fail and indicate failure in a number of different ways.
With this module, we aim to unify microservice error handling by converting
all errors to unambiguous Python exceptions.
"""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import error

class Error(error.UUError):
    """Error for microservice failure"""

    def __init__(self, message, msi_status, msi_code, msi_args, src_exception):
        super(Error, self).__init__(message)
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


# Machinery for wrapping microservices and creating microservice-specific exceptions. {{{

def make(name, error_text):
    """Creates msi wrapper function and exception type as a tuple.
       (see functions below)
    """
    e = _make_exception(name, error_text)
    return (_wrap('msi' + name, e), e)


def _run(msi, exception, *args):
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


def _wrap(msi, exception):
    """Wrap an MSI such that it throws an MSI-specific exception on failure.
       The arguments to the wrapper are the same as that of the msi, only with
       a callback in front.

       e.g.:    callback.msiDataObjCreate(x, y, z)
       becomes: data_obj_create(callback, x, y, z)
    """
    return lambda callback, *args: _run(getattr(callback, msi), exception, *args)


def _make_exception(name, message):
    """Create a msi Error subtype for a specific microservice"""

    t = type('{}Error'.format(name), (Error,), {})
    t.__init__ = lambda self, status, code, args, e = None: \
        super(t, self).__init__(message, status, code, args, e)
    return t


# }}}
# Microservice wrappers {{{

# This naming scheme follows the original msi name, changed to snake_case.
# Note: there is no 'msi_' prefix:
# When imported without '*', these msis are callable as msi.coll_create(), etc.

data_obj_create, DataObjCreateError = make('DataObjCreate', 'Could not create data object')
data_obj_open,   DataObjOpenError   = make('DataObjOpen',   'Could not open data object')
data_obj_read,   DataObjReadError   = make('DataObjRead',   'Could not read data object')
data_obj_write,  DataObjWriteError  = make('DataObjWrite',  'Could not write data object')
data_obj_close,  DataObjCloseError  = make('DataObjClose',  'Could not close data object')
data_obj_copy,   DataObjCopyError   = make('DataObjCopy',   'Could not copy data object')
data_obj_unlink, DataObjUnlinkError = make('DataObjUnlink', 'Could not remove data object')
coll_create,     CollCreateError    = make('CollCreate',    'Could not create collection')
rm_coll,         RmCollError        = make('RmColl',        'Could not remove collection')
check_access,    CheckAccessError   = make('CheckAccess',   'Could not check access')
set_acl,         SetACLError        = make('SetACL',        'Could not set ACL')
get_icat_time,   GetIcatTimeError   = make('GetIcatTime',   'Could not get Icat time')
get_obj_type,    GetObjTypeError    = make('GetObjType',    'Could not get object type')

string_2_key_val_pair, String2KeyValPairError = \
    make('String2KeyValPair', 'Could not create keyval pair')

set_key_value_pairs_to_obj, SetKeyValuePairsToObjError = \
    make('SetKeyValuePairsToObj', 'Could not set metadata on object')

associate_key_value_pairs_to_obj, AssociateKeyValuePairsToObjError = \
    make('AssociateKeyValuePairsToObj', 'Could not associate metadata to object')

# :s/[A-Z]/_\L\0/g

remove_key_value_pairs_from_obj, RemoveKeyValuePairsFromObjError = \
        make('RemoveKeyValuePairsFromObj', 'Could not remove metadata from object')

add_avu, AddAvuError = make('_add_avu', 'Could not add metadata to object')
rmw_avu, RmwAvuError = make('_rmw_avu', 'Could not remove metadata to object')

sudo_obj_acl_set, SudoObjAclSetError = make('SudoObjAclSet', 'Could not set ACLs as admin')

# Add new msis here as needed.

# }}}
