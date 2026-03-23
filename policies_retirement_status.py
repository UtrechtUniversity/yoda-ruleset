"""Policy check functions for data package status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

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
                           path: str,
                           actor: str,
                           status: str) -> None:
    """Post data package status transition actions."""
    status = constants.vault_retirement_state(status)
    # actor = ctx.iiVaultGetActionActor(path, actor, '')['arguments'][2] # TODO: iiAdminVaultRetire

    # Datamanager requests retirement
    if status is constants.vault_retirement_state.RETIREMENT_REQUESTED:
        provenance.log_action(ctx, actor, path, "requested retirement")

        vault_retire.set_requester(ctx, path, actor)

        message = "Data package submitted for retirement"
        # TODO: notify all technical admins

    # Technical admin approves retirement request
    elif status is constants.vault_retirement_state.RETIREMENT_APPROVED:
        provenance.log_action(ctx, actor, path, "approved retirement")

        # TODO: set approver?

        # Send notifications to requester
        requester = vault_retire.get_requester(ctx, path)
        message = "Data package approved for retirement"
        notifications.set(ctx, actor, requester, path, message)

    # Technical admin cancels/denies retirement request
    # Datamanager cancels retirement request
    elif status is constants.vault_retirement_state.ACITVE:
        provenance.log_action(ctx, actor, path, "cancelled retirement")

        # Send notifications to requester or technical admin
        requester = vault_retire.get_requester(ctx, path)
        message = "Data package request for retirement cancelled"
        if actor == requester:  # Requester cancelled request
            notifications.set(ctx, actor, requester, path, message)
        # TODO: elif send notification to technical admin

    # System retires package
    elif status is constants.vault_retirement_state.RETIRED:
        provenance.log_action(ctx, "system", path, "retired")

        # Send notifications to requester and technical admin
        requester = vault_retire.get_requester(ctx, path)
        message = "Data package retired"
        notifications.set(ctx, actor, requester, path, message)
        # TODO: notify approver
