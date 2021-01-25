# -*- coding: utf-8 -*-
"""Policy check functions for datarequest status transitions."""

__copyright__ = "Copyright (c) 2019-2020, Utrecht University"
__license__   = "GPLv3, see LICENSE"

import datarequest
from util import *


def can_set_datarequest_status(ctx, obj_name, status_to):

    # Get current status.
    try:
        status_from = datarequest.status_get_from_path(ctx, obj_name)
    except error.UUError:
        return policy.fail('Could not get current datarequest status')

    # Check if transition is valid.
    transition = (datarequest.status(status_from),
                  datarequest.status(status_to))
    if transition not in datarequest.status_transitions:
        return policy.fail('Illegal datarequest status transition')

    return policy.succeed()

def post_status_transition(ctx, obj_name, value):

     # Send emails
     datarequest.send_emails(ctx, obj_name, value)
