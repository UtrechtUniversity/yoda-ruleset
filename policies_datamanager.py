# -*- coding: utf-8 -*-
""""""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


from util import *


# __all__ = ['rule_uu_can_datamanager_acl_set']

def can_datamanager_acl_set(ctx, obj, actor, other_name, recursive, access):
    x = ctx.iiCanDatamanagerAclSet(obj, actor, other_name, recursive, access, '', '')
    if x['arguments'][5] == '\x01':
        return policy.succeed()
    else:
        return policy.fail(x['arguments'][6])
