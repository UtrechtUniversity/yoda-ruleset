# -*- coding: utf-8 -*-
"""Utility / convenience functions for querying user info."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
from pyblake2 import blake2b

import user


def exists(ctx, grp):
    """Check if a group with the given name exists.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: Boolean indicating if group with given name exists
    """
    return genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsgroup'"
                               .format(grp)).first() is not None


def members(ctx, grp):
    """Get members of a given group.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: Members of given group
    """
    return genquery.Query(ctx, "USER_NAME, USER_ZONE",
                          "USER_GROUP_NAME = '{}' AND USER_TYPE != 'rodsgroup'"
                          .format(grp))


def is_member(ctx, grp, usr=None):
    """Check if a group has a certain member.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name
    :param usr: Given user, otherwise client user is used

    :returns: Boolean indicating if group has a certain member
    """
    return user.is_member_of(ctx, grp, usr)


def get_category(ctx, grp):
    """Get the category of a group.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: Category of given group
    """
    ret = ctx.uuGroupGetCategory(grp, '', '')
    x = ret['arguments'][1]
    return None if x == '' else x


def unique_short_name(ctx, grp):
    """Create unique short name for group in SRAM.

    :param ctx: Combined type of a callback and rei struct
    :param grp: Group name

    :returns: blake2b conversion of zone and group name
    """
    zone = user.zone(ctx)
    concat_string = zone + grp

    # Create hash of 16 characters
    short_name = blake2b(digest_size=8)
    short_name.update(concat_string.encode())

    return short_name.hexdigest()
