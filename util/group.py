# -*- coding: utf-8 -*-
"""Utility / convenience functions for querying user info."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from query import Query


def exists(ctx, grp):
    return Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsgroup'"
                      .format(grp)).first() is not None


def get_category(ctx, grp):
    ret = ctx.uuGroupGetCategory(grp, '', '')
    x = ret['arguments'][1]
    return None if x == '' else x
