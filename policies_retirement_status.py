"""Policy check functions for data package status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import admin
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
    actor = vault_retire.get_latest_actor(ctx, coll)
    if not actor:
        log.write(ctx, "post_status_transition: action actor could not be determined.")  # TODO: block the rest of the function? or just use empty string?

    # Datamanager requests retirement
    if status is constants.vault_retirement_state.RETIREMENT_REQUESTED:
        # Update provenance log
        provenance.log_action(ctx, actor, coll, "requested retirement")

        # Set actor
        vault_retire.set_retirement_requester(ctx, coll, actor)

        # Send notifications to admins
        message = "Data package submitted for retirement"

        admins = admin.get_admins(ctx)
        if len(admins) > 0:
            for adm in admins:
                notifications.set(ctx, actor, adm, coll, message)
        else:
            log.write(ctx, "post_status_transition: could not notify admins.")

    # Admin approves retirement request
    elif status is constants.vault_retirement_state.RETIREMENT_APPROVED:
        # Update provenance log
        provenance.log_action(ctx, actor, coll, "approved retirement")

        # Set actor
        vault_retire.set_retirement_approver(ctx, coll, actor)

        # Send notifications to requester
        message = "Data package approved for retirement"

        requester = vault_retire.get_retirement_requester(ctx, coll)
        notifications.set(ctx, actor, requester, coll, message)

    # Admin cancels/denies retirement request
    # Datamanager cancels retirement request
    elif status is constants.vault_retirement_state.ACTIVE:
        # Update provenance log
        provenance.log_action(ctx, actor, coll, "cancelled retirement")

        # Send notifications to requester or admins
        message = "Data package request for retirement cancelled"

        requester = vault_retire.get_retirement_requester(ctx, coll)
        if actor != requester:  # Admin cancelled -> notify requester
            notifications.set(ctx, actor, requester, coll, message)
        else:  # Requested cancelled -> notify admins
            admins = admin.get_admins(ctx)
            if len(admins) > 0:
                for adm in admins:
                    notifications.set(ctx, actor, adm, coll, message)
            else:
                log.write(ctx, "post_status_transition: could not notify admins.")

    # System retires package
    elif status is constants.vault_retirement_state.RETIRED:
        # Update provenance log
        provenance.log_action(ctx, "system", coll, "retired")

        # Send notifications to requester and technical admin
        message = "Data package retired"

        actors = []
        requester = vault_retire.get_retirement_requester(ctx, coll)
        actors.append(requester)
        approver = vault_retire.get_retirement_approver(ctx, coll)
        actors.append(approver)

        for actor in actors:
            notifications.set(ctx, actor, requester, coll, message)
