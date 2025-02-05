"""Policy check functions for datamanager actions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *


def can_datamanager_acl_set(ctx: rule.Context,
                            obj: str,
                            actor: str,
                            other_name: str,
                            recursive: str,
                            access: str) -> policy.Succeed | policy.Fail:
    x = ctx.iiCanDatamanagerAclSet(obj, actor, other_name, recursive, access, '', '')
    if x['arguments'][5] == '\x01':
        return policy.succeed()
    else:
        return policy.fail(x['arguments'][6])
