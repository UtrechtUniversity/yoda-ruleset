# -*- coding: utf-8 -*-
"""Functions for admin access check."""

__copyright__ = 'Copyright 2024, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

__all__ = [
    'api_admin_has_access',
]

from util import *


@api.make()
def api_admin_has_access(ctx):
    """
    Checks if the user has admin access based on user rights or membership in admin-priv group.

    :param ctx: Combined type of a ctx and rei struct

    :returns: True if the user has the admin access, False otherwise.
    """

    group_name = "priv-admin"

    # if user has admin right
    is_admin = user.is_admin(ctx)

    # if user is in the privilege group
    in_priv_group = user.is_member_of(ctx, group_name)

    return is_admin or in_priv_group
