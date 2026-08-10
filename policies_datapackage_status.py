"""Policy check functions for data package status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import folder
import meta
import notifications
import provenance
import vault
from metadata_utils import is_json_metadata_valid
from util import *


def pre_status_transition(ctx: rule.Context,
                          coll: str,
                          current: constants.research_package_state,
                          new: constants.research_package_state) -> policy.Succeed | policy.Fail:
    """Placeholder for action taken before status transition."""

    return policy.succeed()


def can_transition_datapackage_status(ctx: rule.Context,
                                      actor: str,
                                      coll: str,
                                      status_from: str,
                                      status_to: str) -> policy.Succeed | policy.Fail:
    transition = (constants.vault_package_state(status_from),
                  constants.vault_package_state(status_to))
    if transition not in constants.datapackage_transitions:
        return policy.fail('Illegal status transition')

    if status_to is constants.vault_package_state.SUBMITTED_FOR_PUBLICATION:
        meta_path = meta.get_latest_vault_metadata_path(ctx, coll)
        if meta_path is None:
            return policy.fail('Metadata missing, unable to submit this data package for publication.')

        if not is_json_metadata_valid(ctx, meta_path):
            return policy.fail('Metadata is incomplete or invalid, please open the metadata form for more information')

    return policy.succeed()


def can_set_datapackage_status_attr(ctx: rule.Context,
                                    actor: str,
                                    coll: str,
                                    status: str) -> policy.Succeed | policy.Fail:
    try:
        new = constants.vault_package_state(status)
    except ValueError:
        return policy.fail('New datapackage status attribute is invalid')

    current = vault.get_coll_vault_status(ctx, coll)

    x = can_transition_datapackage_status(ctx, actor, coll, current, new)
    if not x:
        return x
    else:
        return (current, new)


def post_status_transition(ctx: rule.Context,
                           path: str,
                           actor: str,
                           status: str) -> None:
    """Post data package status transition actions."""
    status = constants.vault_package_state(status)
    actor = vault.get_latest_action_actor(ctx, path) or actor

    if status is constants.vault_package_state.UNPUBLISHED:
        provenance_log = provenance.get_provenance_log(ctx, path)

        if provenance_log[0][1] != "canceled publication":
            if provenance_log[0][1] == "submitted for publication":
                # If previous action was "submitted for publication"
                # and new status is UNPUBLISHED action is canceled publication
                # else action is secured in vault.
                provenance.log_action(ctx, actor, path, "canceled publication")
            else:
                provenance.log_action(ctx, "system", path, "secured in vault")

    elif status is constants.vault_package_state.SUBMITTED_FOR_PUBLICATION:
        provenance.log_action(ctx, actor, path, "submitted for publication")

        # Store actor of submitted for publication.
        vault.set_submitter(ctx, path, actor)

        try:
            datamanagers = folder.get_datamanagers(ctx, path)
        except ValueError as e:
            log.write(ctx, f"Unable to send submitted for publication notifications for <{path}>: cannot get data managers: {str(e)}")
            datamanagers = []

        if len(datamanagers) > 0:
            # Send notifications to datamanagers.
            message = "Data package submitted for publication"
            for datamanager in datamanagers:
                datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
                notifications.set(ctx, actor, datamanager_name, path, message)

    elif status is constants.vault_package_state.APPROVED_FOR_PUBLICATION:
        provenance.log_action(ctx, actor, path, "approved for publication")

        # Store actor of publication approval.
        vault.set_approver(ctx, path, actor)

        # Send notifications to submitter.
        submitter = vault.get_submitter(ctx, path)
        message = "Data package approved for publication"
        notifications.set(ctx, actor, submitter, path, message)

    elif status is constants.vault_package_state.PUBLISHED:
        actor = "system"
        provenance.log_action(ctx, actor, path, "published")

        # Send notifications to submitter and approver.
        submitter = vault.get_submitter(ctx, path)
        approver = vault.get_approver(ctx, path)
        message = "Data package published"
        notifications.set(ctx, actor, submitter, path, message)
        notifications.set(ctx, actor, approver, path, message)

    elif status is constants.vault_package_state.PENDING_DEPUBLICATION:
        provenance.log_action(ctx, actor, path, "requested depublication")

    elif status is constants.vault_package_state.DEPUBLISHED:
        actor = "system"
        provenance.log_action(ctx, actor, path, "depublication")

        # Send notifications to submitter and approver.
        submitter = vault.get_submitter(ctx, path)
        approver = vault.get_approver(ctx, path)
        message = "Data package depublished"
        notifications.set(ctx, actor, submitter, path, message)
        notifications.set(ctx, actor, approver, path, message)

    elif status is constants.vault_package_state.PENDING_REPUBLICATION:
        provenance.log_action(ctx, actor, path, "requested republication")
