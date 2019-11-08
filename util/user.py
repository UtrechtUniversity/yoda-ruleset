# -*- coding: utf-8 -*-
"""Utility / convenience functions for querying user info."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import session_vars
import genquery

def user_and_zone(ctx):
    client = session_vars.get_map(ctx.rei)['client_user']
    return client['user_name'], client['irods_zone']

def full_name(ctx):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return '{}#{}'.format(*user_and_zone(ctx))

def name(ctx):
    return session_vars.get_map(ctx.rei)['client_user']['user_name']

def zone(ctx):
    return session_vars.get_map(ctx.rei)['client_user']['irods_zone']

def user_type(ctx):
    """Obtain user type."""
    for row in genquery.row_iterator("USER_TYPE",
                                     "USER_NAME = '{}' AND USER_ZONE = '{}'".format(*user_and_zone(ctx)),
                                     genquery.AS_LIST, ctx):
        return row[0]
    return ''

# TODO: Remove. {{{
def get_client_name_zone(rei):
    """Obtain client name and zone, as a tuple"""
    client = session_vars.get_map(rei)['client_user']
    return client['user_name'], client['irods_zone']

# TODO: Replace calls (meta.py) with full_name.
def get_client_full_name(rei):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return '{}#{}'.format(*get_client_name_zone(rei))
# }}}

def name_from_id(callback, user_id):
    """Retrieve username from user ID."""
    for row in genquery.row_iterator("USER_NAME",
                                     "USER_ID = '{}'".format(user_id),
                                     genquery.AS_LIST, callback):
        return row[0]
    return ''
