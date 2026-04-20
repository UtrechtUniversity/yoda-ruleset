"""Functions for admin module."""

__copyright__ = 'Copyright 2024-2026, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

__all__ = [
    'api_admin_has_access',
]

import genquery

from util import *


@api.make()
def api_admin_has_access(ctx: rule.Context) -> api.Result:
    """
    Checks if the user is admin (i.e., has admin access based on user rights or membership in admin-priv group).

    :param ctx: Combined type of a ctx and rei struct

    :returns: True if the user has the admin access, False otherwise.
    """
    return is_admin(ctx, user.name(ctx))


def is_admin(ctx: rule.Context, user: str) -> bool:
    """Checks if user is admin"""
    return user in get_admins(ctx)


def get_admins(ctx: rule.Context) -> list:
    """Get all admin users (users that have admin access based on user rights or membership of priv-admin)"""
    rodsadmins = user.get_rodsadmins(ctx)
    privadmins = []
    for row in genquery.row_iterator("USER_NAME",
                                     "USER_GROUP_NAME = 'priv-admin'",
                                     genquery.AS_LIST, ctx):
        privadmins.append(row[0])

    admins = set(rodsadmins + privadmins)

    return list(admins)
