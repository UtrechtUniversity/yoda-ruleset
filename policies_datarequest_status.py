"""Policy check functions for datarequest status transitions."""
from __future__ import annotations

__copyright__ = "Copyright (c) 2019-2025, Utrecht University"
__license__   = "GPLv3, see LICENSE"

import re

import datarequest
from util import *


def can_set_datarequest_status(ctx: rule.Context,
                               obj_name: str,
                               status_to: str) -> policy.Succeed | policy.Fail:
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


def post_status_transition(ctx: rule.Context, obj_name: str, value: str) -> None:
    # Write timestamp to provenance log
    request_id = re.sub(r"^[^0-9]*/(\d+).*", r"\1", obj_name)
    status     = datarequest.status[value]
    datarequest.datarequest_provenance_write(ctx, request_id, status)

    # Send emails
    datarequest.send_emails(ctx, obj_name, value)
