# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with users."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import session_vars
import genquery

def get_client_name_zone(rei):
    """Obtain client name and zone, as a tuple"""
    client = session_vars.get_map(rei)['client_user']
    return client['user_name'], client['irods_zone']


def get_client_full_name(rei):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return '{}#{}'.format(*get_client_name_zone(rei))


def name_from_id(callback, user_id):
    """Retrieve username from user ID."""
    for row in genquery.row_iterator("USER_NAME",
                                     "USER_ID = '{}'".format(user_id),
                                     genquery.AS_LIST, callback):
        return row[0]
    return ''
