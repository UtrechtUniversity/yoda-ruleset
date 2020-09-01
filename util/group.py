# -*- coding: utf-8 -*-
"""Utility / convenience functions for querying user info."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from query import Query
import user


def exists(ctx, grp):
    """
    Check if a group with the given name exists.

    :param grp: Group name
    """
    return Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsgroup'"
                      .format(grp)).first() is not None


def members(ctx, grp):
    """
    Get members of a given group.

    :param grp: Group name
    """
    return Query(ctx, "USER_NAME, USER_ZONE",
                 "USER_GROUP_NAME = '{}' AND USER_TYPE != 'rodsgroup'"
                 .format(grp))


def is_member(ctx, grp, usr=None):
    """
    Check if a group has a certain member.

    :param grp: Group name
    """
    return user.is_member_of(ctx, grp, usr)


def get_category(ctx, grp):
    """
    Get the category of a group.

    :param grp: Group name
    """
    ret = ctx.uuGroupGetCategory(grp, '', '')
    x = ret['arguments'][1]
    return None if x == '' else x
