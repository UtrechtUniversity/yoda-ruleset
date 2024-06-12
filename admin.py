# -*- coding: utf-8 -*-
"""Functions for administration management."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = [
           'api_group_user_is_admin',
]

from util import *

@api.make()
def api_admin_is_user_admin(ctx):# Nameing convention api_<module name>_<func name>
    """Check if user is admin.
    TODO: Add docstrings
    """
    #TODO: user name available in this module no need to pass arg in portal
    # TODO: Playaround with other parameters in user.py 
    log.write(ctx, "Test api_group_user_is_admin success, from Ruleset") #TODO: Test logging
    
    return True
