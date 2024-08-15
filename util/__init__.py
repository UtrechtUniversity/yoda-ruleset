# -*- coding: utf-8 -*-
"""Generic UU ruleset utility functions and types.

This subpackage does not export any callable rules by itself.
Rather, it provides utility Python functions to other rules.
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys

# Make sure that importing * from this package gives (qualified) access to all
# contained modules.
# i.e. importing code can use these modules like: collection.exists(callback, 'bla')

import yoda_names

if 'unittest' not in sys.modules:
    # We don't import everything when running unit tests, because then we'll have
    # to deal with all the dependencies. Functions that have unit tests should
    # import utils specifically
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
    import resource
    import arb_data_manager
    import cached_data_manager
    import irods_type_info

    # Config items can be accessed directly as 'config.foo' by any module
    # that imports * from util.
    from config import config

    if config.enable_data_package_archive or config.enable_data_package_download:
        import bagit

    if config.environment == 'development':
        ping = api_ping = api.make()(lambda ctx, x=42: x)
