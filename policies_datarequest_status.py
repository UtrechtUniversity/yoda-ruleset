# -*- coding: utf-8 -*-
"""Policy check functions for datarequest status transitions."""

__copyright__ = "Copyright (c) 2019-2020, Utrecht University"
__license__   = "GPLv3, see LICENSE"

import datarequest

from util import *


def can_set_datarequest_status(ctx, actor, obj_name, status_to):
    # Check if user is rods.
    if actor != "rods":
        return policy.fail('No permission to change datarequest status')

    # Check if user is admin.
    if not user.is_admin(ctx, actor):
        return policy.fail('No permission to change datarequest status')

    # Get current status.
    try:
        status_from = datarequest.status_get_from_path(ctx, path)
    except error.UUError:
        return policy.fail('Could not get current datarequest status')

    transition = (datarequest.status(status_from),
                  datarequest.status(status_to))
    if transition not in datarequest.status_transitions:
        return policy.fail('Illegal datarequest status transition')

    return policy.succeed()
