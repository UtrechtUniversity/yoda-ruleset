# -*- coding: utf-8 -*-
"""Generic UU ruleset utility functions and types.

This subpackage does not export any callable rules by itself.
Rather, it provides utility Python functions to other rules.
"""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

# Make sure that importing * from this package gives (qualified) access to all
# contained modules.
# i.e. importing code can use these modules like: collection.exists(callback, 'bla')
__all__ = ['log',
           'error',
           'jsonutil',
           'rule',
           'api',
           'msi',
           'pathutil',
           'constants',
           'collection',
           'data_object',
           'user',
           'query',
           'config']

# Config items can be accessed directly as 'config.foo' by any module
# that imports * from util.
from config import config
