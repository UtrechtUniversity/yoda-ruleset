# -*- coding: utf-8 -*-
"""Generic UU ruleset utility functions and types.

This subpackage does not export any callable rules by itself.
Rather, it provides utility Python functions to other rules.
"""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

# Make sure that importing * from this package gives (qualified) access to all
# contained modules.
# i.e. importing code can use these modules like: collection.exists(callback, 'bla')

import log
import error
import jsonutil
import rule
import api
import msi
import policy
import pathutil
import constants
import collection
import data_object
import user
import group
import avu
import misc
import config
import resource
import arb_data_manager
import cached_data_manager

# Config items can be accessed directly as 'config.foo' by any module
# that imports * from util.
from config import config

if config.enable_data_package_archive or config.enable_data_package_download:
    import bagit


if config.environment == 'development':
    import irods_type_info
    ping = api_ping = api.make()(lambda ctx, x=42: x)
