# -*- coding: utf-8 -*-
"""Functions for admin access check."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

__all__ = [
    'api_admin_has_access',
]

from util import *


@api.make()
def api_admin_has_access(ctx):  # TODO: Update the default group-> create a new one priv-admin # Add the group by groupmanagersetup.sh
    """
    Checks if the user has admin access based on user rights or membership in group priv-group-add".

    :param ctx:         Combined type of a ctx and rei struct

    :returns: True if the user has the admin access, False otherwise.
    """

    group_name="priv-group-add" #TODO: change to another group, and search replace all 

    # if user has admin right #TODO: IMPROVE CODES, try except blocks?
    is_admin = user.is_admin(ctx)
    log.write(ctx, "user name is: " + str(user.name(ctx)))  
    log.write(ctx, "is_admin?: " + str(is_admin))  
    log.write(ctx, "usertype is: " + str(user.user_type(ctx)))  

    # if user is in the privilege group
    in_priv_group = user.is_member_of(ctx, group_name)
    log.write(ctx, "priv  group_name?: " + str(group_name))  
    log.write(ctx, "in_priv_group?: " + str(in_priv_group))  

    return is_admin or in_priv_group
