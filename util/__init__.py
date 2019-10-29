# -*- coding: utf-8 -*-
"""Generic UU ruleset utility functions and types.

This subpackage does not export any callable rules by itself.
Rather, it provides utility Python functions to other rules.
"""

# Make sure that importing * from this package gives (qualified) access to all
# contained modules.
# i.e. importing code can use these modules like: collection.exists(callback, 'bla')
__all__ = ['error',
           'jsonutil',
           'rule',
           #'api',
           'msi',
           'pathutil',
           'constants',
           'collection',
           'data_object',
           'user']
