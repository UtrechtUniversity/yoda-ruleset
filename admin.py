# -*- coding: utf-8 -*-
"""Functions for administration management."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

__all__ = [
    'api_admin_has_access',
]

from util import *


@api.make()
def api_admin_has_access(ctx, group_name="priv-group-add"):  # TODO: Update the default group
    """
    Checks if the user has admin access based on user rights or membership in a specified group.

    :param ctx:         Combined type of a ctx and rei struct
    :param group_name:  The name of the privilege group to check against. Defaults to "priv-group-add".

    :returns: True if the user has the admin access, False otherwise.
    """
    # if user has admin right
    is_admin = user.is_admin(ctx)
    log.write(ctx, "is_admin?: " + str(is_admin))  # Corrected space after ':'
    log.write(ctx, "usertype is: " + str(user.user_type(ctx)))  # Corrected space after ':'

    # if user is in the privilege group
    in_priv_group = user.is_member_of(ctx, group_name)
    log.write(ctx, "in_priv_group?: " + str(in_priv_group))  # Corrected space after ':'

    return is_admin or in_priv_group
