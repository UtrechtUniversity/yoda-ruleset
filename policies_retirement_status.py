"""Policy check functions for data package status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

import notifications
import provenance
import vault
import vault_retire
from util import *


def pre_status_transition(ctx: rule.Context,
                          coll: str,
                          current: constants.vault_retirement_state,
                          new: constants.vault_retirement_state) -> policy.Succeed | policy.Fail:
    """Placeholder for action taken before status transition."""

    return policy.succeed()


def can_transition_retirement_status(ctx: rule.Context,
                                     coll: str,
                                     status_from: str,
                                     status_to: str) -> policy.Succeed | policy.Fail:
    """Check if retirement status transition action is legal."""
    transition = (constants.vault_retirement_state(status_from),
                  constants.vault_retirement_state(status_to))
    if transition not in constants.retirement_transitions:
        return policy.fail('Illegal status transition')

    # If vault package is not unpublished, published, or depublished then retirement cannot be requested
    vault_status = vault.get_coll_vault_status(ctx, coll)
    if vault_status not in [constants.vault_package_state.UNPUBLISHED, constants.vault_package_state.PUBLISHED, constants.vault_package_state.DEPUBLISHED]:
        return policy.fail('Illegal status transition')

    return policy.succeed()


def post_status_transition(ctx: rule.Context,
                           coll: str,
                           status: str) -> None:
    """Post retirement status transition actions."""
    status = constants.vault_retirement_state(status)

    iter = list(genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}retirement_action_%' AND META_COLL_ATTR_VALUE like '%{coll}%{status.value}%'",
        genquery.AS_LIST,
        ctx
    ))
    data = jsonutil.parse(iter[0][1])
    actor = data[2]

    # Datamanager requests retirement
    if status is constants.vault_retirement_state.RETIREMENT_REQUESTED:
        provenance.log_action(ctx, actor, coll, "requested retirement")

        vault_retire.set_retirement_requester(ctx, coll, actor)

        message = "Data package submitted for retirement"
        # TODO: notify all technical admins

    # # Technical admin approves retirement request
    # elif status is constants.vault_retirement_state.RETIREMENT_APPROVED:
    #     provenance.log_action(ctx, actor, coll, "approved retirement")

    #     # TODO: set approver

    #     # Send notifications to requester
    #     requester = vault_retire.get_retirement_requester(ctx, coll)
    #     message = "Data package approved for retirement"
    #     notifications.set(ctx, actor, requester, coll, message)

    # Technical admin cancels/denies retirement request
    # Datamanager cancels retirement request
    elif status is constants.vault_retirement_state.ACTIVE:
        provenance.log_action(ctx, actor, coll, "cancelled retirement")

        # Send notifications to requester or technical admin
        requester = vault_retire.get_retirement_requester(ctx, coll)
        message = "Data package request for retirement cancelled"
        if actor != requester:  # Technical admin cancelled -> notify requester
            notifications.set(ctx, actor, requester, coll, message)
        else:  # Requested cancelled -> notify technical admins
            # TODO: get approver
            log.write(ctx, "Requester cancelled")

    # # System retires package
    # elif status is constants.vault_retirement_state.RETIRED:
    #     provenance.log_action(ctx, "system", coll, "retired")

    #     # Send notifications to requester and technical admin
    #     requester = vault_retire.get_retirement_requester(ctx, coll)
    #     message = "Data package retired"
    #     notifications.set(ctx, actor, requester, coll, message)
    #     # TODO: notify approver too
