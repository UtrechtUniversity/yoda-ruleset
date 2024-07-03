# -*- coding: utf-8 -*-
"""Functions for admin module."""

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
    # Check if user is admin.
    is_admin = user.is_admin(ctx)

    # Check if user is in the priv-admin group.
    in_priv_group = user.is_member_of(ctx, "priv-admin")

    return is_admin or in_priv_group
