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
User.__str__ = lambda self: f'{self.name}#{self.zone}'


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

    return genquery.Query(ctx, "USER_TYPE", f"USER_NAME = '{user[0]}' AND USER_ZONE = '{user[1]}'").first() in ["rodsuser", "rodsadmin"]


def get_type(ctx: 'rule.Context', user: str | User | None = None) -> str:
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
                          f"USER_NAME = '{user[0]}' AND USER_ZONE = '{user[1]}'").first()


def is_rodsadmin(ctx: 'rule.Context', user: str | User | None = None) -> bool:
    """Check if user is an rodsadmin."""
    return get_type(ctx, user) == 'rodsadmin'


def is_member_of(ctx: 'rule.Context', group: str, user: str | User | None = None) -> bool:
    """Check if user is member of given group."""
    if user is None:
        user = user_and_zone(ctx)
    elif type(user) is str:
        user = from_str(ctx, user)

    return genquery.Query(ctx, 'USER_GROUP_NAME',
                          f"USER_NAME = '{user[0]}' AND USER_ZONE = '{user[1]}' AND USER_GROUP_NAME = '{group}'").first() is not None


def name_from_id(ctx: 'rule.Context', user_id: str) -> str:
    """Retrieve username from user ID."""
    for row in genquery.row_iterator("USER_NAME",
                                     f"USER_ID = '{user_id}'",
                                     genquery.AS_LIST, ctx):
        return row[0]
    return ''


def id_from_name(ctx: 'rule.Context', user_name: str) -> str:
    """Retrieve user ID based on user name."""
    for row in genquery.row_iterator("USER_ID",
                                     f"USER_NAME = '{user_name}'",
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


def get_rodsadmins(ctx: 'rule.Context') -> list:
    """Get all rodsadmin users."""
    rodsadmins = []
    for row in genquery.row_iterator("USER_NAME",
                                     "USER_TYPE = 'rodsadmin'",
                                     genquery.AS_LIST, ctx):
        rodsadmins.append(row[0])
    return rodsadmins
