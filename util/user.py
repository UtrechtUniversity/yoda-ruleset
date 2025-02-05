"""Utility / convenience functions for querying user info."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import subprocess
from collections import namedtuple
from typing import TYPE_CHECKING

import genquery
import session_vars

import log
if TYPE_CHECKING:
    import rule

# User is a tuple consisting of a name and a zone, which stringifies into 'user#zone'.
User = namedtuple('User', ['name', 'zone'])
User.__str__ = lambda self: '{}#{}'.format(*self)


def user_and_zone(ctx: 'rule.Context') -> User:
    """Obtain client name and zone."""
    client = session_vars.get_map(ctx.rei)['client_user']
    return User(client['user_name'], client['irods_zone'])


def full_name(ctx: 'rule.Context') -> str:
    """Obtain client name and zone, formatted as a 'x#y' string."""
    return str(user_and_zone(ctx))


def name(ctx: 'rule.Context') -> str:
    """Get the name of the client user."""
    return session_vars.get_map(ctx.rei)['client_user']['user_name']


def zone(ctx: 'rule.Context') -> str:
    """Get the zone of the client user."""
    return session_vars.get_map(ctx.rei)['client_user']['irods_zone']


def from_str(ctx: 'rule.Context', s: str) -> User:
    """Create a (user,zone) tuple from a user[#zone] string.

    If no zone is present in the string, the client's zone is used.

    :param ctx: Combined type of a callback and rei struct
    :param s:   User string (user[#zone])

    :returns: A (user,zone) tuple
    """
    parts = s.split('#')
    if len(parts) < 2 or len(parts[1]) == 0:
        # Take zone from client zone when not present.
        return User(parts[0], zone(ctx))
    else:
        return User(*parts)


def exists(ctx: 'rule.Context', user: str | User) -> bool:
    """Check if a user ('rodsuser' or 'rodsadmin') exists.

    :param ctx:  Combined type of a callback and rei struct
    :param user: Given user

    :returns: Boolean indicating if user exists
    """
    if type(user) is str:
        user = from_str(ctx, user)

    return genquery.Query(ctx, "USER_TYPE", "USER_NAME = '{}' AND USER_ZONE = '{}'".format(*user)).first() in ["rodsuser", "rodsadmin"]


def user_type(ctx: 'rule.Context', user: str | User | None = None) -> str:
    """Return the user type ('rodsuser' or 'rodsadmin') for the given user, or the client user if no user is given.

    If the user does not exist, None is returned.

    :param ctx:  Combined type of a callback and rei struct
    :param user: Given user, otherwise client user is used

    :returns: User type ('rodsuser' or 'rodsadmin')
    """
    if user is None:
        user = user_and_zone(ctx)
    elif type(user) is str:
        user = from_str(ctx, user)

    return genquery.Query(ctx, "USER_TYPE",
                          "USER_NAME = '{}' AND USER_ZONE = '{}'".format(*user)).first()


def is_admin(ctx: 'rule.Context', user: str | User | None = None) -> bool:
    """Check if user is an admin."""
    return user_type(ctx, user) == 'rodsadmin'


def is_member_of(ctx: 'rule.Context', group: str, user: str | User | None = None) -> bool:
    """Check if user is member of given group."""
    if user is None:
        user = user_and_zone(ctx)
    elif type(user) is str:
        user = from_str(ctx, user)

    return genquery.Query(ctx, 'USER_GROUP_NAME',
                          "USER_NAME = '{}' AND USER_ZONE = '{}' AND USER_GROUP_NAME = '{}'"
                          .format(*list(user) + [group])).first() is not None


def name_from_id(ctx: 'rule.Context', user_id: str) -> str:
    """Retrieve username from user ID."""
    for row in genquery.row_iterator("USER_NAME",
                                     "USER_ID = '{}'".format(user_id),
                                     genquery.AS_LIST, ctx):
        return row[0]
    return ''


def number_of_connections(ctx: 'rule.Context') -> int:
    """Get number of active connections from client user."""
    connections = 0
    try:
        # We don't use the -a option with the ips command, because this takes
        # significantly more time, which would significantly reduce performance.
        ips = (subprocess.check_output(["ips"])).decode("utf-8")
        username = session_vars.get_map(ctx.rei)['client_user']['user_name']
        connections = ips.count(username)
    except Exception as e:
        log.write(ctx, "Error: unable to determine number of user connections: " + str(e))
        return 0

    return connections
