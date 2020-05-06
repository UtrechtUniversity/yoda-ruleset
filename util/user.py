# -*- coding: utf-8 -*-
"""Utility / convenience functions for querying user info."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import session_vars
import genquery
from query import Query
import query
from collections import namedtuple

# User is a tuple consisting of a name and a zone, which stringifies into 'user#zone'.
User = namedtuple('User', ['name', 'zone'])
User.__str__ = lambda self: '{}#{}'.format(*self)


def user_and_zone(ctx):
    client = session_vars.get_map(ctx.rei)['client_user']
    return User(client['user_name'], client['irods_zone'])


def full_name(ctx):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    return str(user_and_zone(ctx))


def name(ctx):
    """Gets the name of the client user"""
    return session_vars.get_map(ctx.rei)['client_user']['user_name']


def zone(ctx):
    """Gets the zone of the client user"""
    return session_vars.get_map(ctx.rei)['client_user']['irods_zone']


def from_str(ctx, s):
    """Returns a (user,zone) tuple from a user[#zone] string.

    If no zone is present in the string, the client's zone is used.
    """
    parts = s.split('#')
    if len(parts) < 2 or len(parts[1]) == 0:
        # Take zone from client zone when not present.
        return User(parts[0], zone(ctx))
    else:
        return User(*parts)


def exists(ctx, user):
    if type(user) is str:
        user = from_str(ctx, user)

    return Query(ctx, "USER_TYPE", "USER_NAME = '{}' AND USER_ZONE = '{}'".format(*user)).first() is not None


def user_type(ctx, user=None):
    """Returns the user type ('rodsuser' or 'rodsadmin') for the given user, or the client user if no user is given.

    If the user does not exist, None is returned.
    """
    if user is None:
        user = user_and_zone(ctx)
    elif type(user) is str:
        user = from_str(ctx, user)

    return Query(ctx, "USER_TYPE",
                      "USER_NAME = '{}' AND USER_ZONE = '{}'".format(*user)).first()


def is_admin(ctx, user=None):
    return user_type(ctx, user) == 'rodsadmin'


def is_member_of(ctx, group, user=None):
    if user is None:
        user = user_and_zone(ctx)
    elif type(user) is str:
        user = from_str(ctx, user)

    return Query(ctx, 'USER_GROUP_NAME',
                      "USER_NAME = '{}' AND USER_ZONE = '{}' AND USER_GROUP_NAME = '{}'"
                      .format(*list(user) + [group])).first() is not None


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
