"""Policy check functions for data package status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import admin
import notifications
import provenance
import vault
import vault_deaccession
from util import *


def pre_status_transition(ctx: rule.Context,
                          coll: str,
                          current: constants.vault_deaccession_state,
                          new: constants.vault_deaccession_state) -> policy.Succeed | policy.Fail:
    """Placeholder for action taken before status transition."""

    return policy.succeed()


def can_transition_deaccession_status(ctx: rule.Context,
                                      coll: str,
                                      status_from: str,
                                      status_to: str) -> policy.Succeed | policy.Fail:
    """Check if deaccession status transition action is legal."""
    transition = (constants.vault_deaccession_state(status_from),
                  constants.vault_deaccession_state(status_to))
    if transition not in constants.deaccession_transitions:
        return policy.fail('Illegal status transition')

    # If vault package is not unpublished, published, or depublished then deaccession cannot be requested
    vault_status = vault.get_coll_vault_status(ctx, coll)
    if vault_status not in [constants.vault_package_state.UNPUBLISHED, constants.vault_package_state.PUBLISHED, constants.vault_package_state.DEPUBLISHED]:
        return policy.fail('Illegal status transition')

    return policy.succeed()


def post_status_transition(ctx: rule.Context,
                           coll: str,
                           status: str) -> None:
    """Post deaccession status transition actions."""
    status = constants.vault_deaccession_state(status)

    # Datamanager requests deaccession
    if status is constants.vault_deaccession_state.DEACCESSION_REQUESTED:
        # Get actor
        actor = vault_deaccession.get_deaccession_actor(ctx, coll, "request")

        # Update provenance log
        provenance.log_action(ctx, actor, coll, "submitted for deaccession")

        # Send notifications to admins
        message = "Data package submitted for deaccession"

        admins = admin.get_admins(ctx)
        if len(admins) > 0:
            for adm in admins:
                if adm != "rods":  # Skip rods
                    notifications.set(ctx, actor, adm, coll, message)
        else:
            log.write(ctx, "post_status_transition: could not notify admins.")

    # Admin approves deaccession request
    elif status is constants.vault_deaccession_state.DEACCESSION_APPROVED:
        # Get actor
        actor = vault_deaccession.get_deaccession_actor(ctx, coll, "approval")

        # Update provenance log
        provenance.log_action(ctx, actor, coll, "approved for deaccession")

        # Send notifications to requester
        message = "Data package approved for deaccession"

        requester = vault_deaccession.get_deaccession_actor(ctx, coll, "request")
        notifications.set(ctx, actor, requester, coll, message)

        vault_deaccession.initialize_deaccession(ctx, coll)

    # Admin cancels/denies deaccession request
    # Datamanager cancels deaccession request
    elif status is constants.vault_deaccession_state.ACTIVE:
        # Get actor
        actor = vault_deaccession.get_deaccession_actor(ctx, coll, "cancelation")

        # Update provenance log
        provenance.log_action(ctx, actor, coll, "withdrawn from deaccession")

        # Send notifications to requester or admins
        message = "Data package withdrawn from deaccession"

        requester = vault_deaccession.get_deaccession_actor(ctx, coll, "request")
        if actor != requester:  # Admin cancelled -> notify requester
            notifications.set(ctx, actor, requester, coll, message)
        else:  # Requester cancelled -> notify admins
            admins = admin.get_admins(ctx)
            if len(admins) > 0:
                for adm in admins:
                    if adm != "rods":  # Skip rods
                        notifications.set(ctx, actor, adm, coll, message)
            else:
                log.write(ctx, "post_status_transition: could not notify admins.")

        vault_deaccession.cleanup_deaccession_cancel(ctx, coll)

    # System deaccessions package
    elif status is constants.vault_deaccession_state.DEACCESSION_COMPLETE:
        # Update provenance log
        provenance.log_action(ctx, "system", coll, "deaccessioned")

        # Send notifications to requester and approver
        message = "Data package deaccessioned"

        actors = []
        requester = vault_deaccession.get_deaccession_actor(ctx, coll, "request")
        actors.append(requester)
        approver = vault_deaccession.get_deaccession_actor(ctx, coll, "approval")
        actors.append(approver)

        for actor in actors:
            notifications.set(ctx, actor, requester, coll, message)
