# -*- coding: utf-8 -*-
"""Miscellaneous functions for interacting with iRODS."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import msi
import irods_types


def kvpair(ctx, k, v):
    """Create a keyvalpair object, needed by certain msis."""
    return msi.string_2_key_val_pair(ctx, '{}={}'.format(k, v), irods_types.BytesBuf())['arguments'][1]
