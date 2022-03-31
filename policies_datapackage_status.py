# -*- coding: utf-8 -*-
"""Policy check functions for data package status transitions."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import folder
import meta
import notifications
import provenance
import vault
from util import *


def pre_status_transition(ctx, coll, current, new):
    """Action taken before status transition."""
    if current is constants.vault_package_state.SUBMITTED_FOR_PUBLICATION \
       and new is constants.vault_package_state.UNPUBLISHED:
        action_actor = provenance.latest_action_actor(ctx, coll)
        provenance.log_action(ctx, action_actor, coll, "canceled publication")

    return policy.succeed()


def can_transition_datapackage_status(ctx, actor, coll, status_from, status_to):
    transition = (constants.vault_package_state(status_from),
                  constants.vault_package_state(status_to))
    if transition not in constants.datapackage_transitions:
        return policy.fail('Illegal status transition')

    if status_to is constants.vault_package_state.SUBMITTED_FOR_PUBLICATION:
        meta_path = meta.get_latest_vault_metadata_path(ctx, coll)
        if meta_path is None:
            return policy.fail('Metadata missing, unable to submit this data package for publication.')

        if not meta.is_json_metadata_valid(ctx, meta_path):
            return policy.fail('Metadata is not valid, please open the metadata form for more information')

    return policy.succeed()


def can_set_datapackage_status_attr(ctx, actor, coll, status):
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


def post_status_transition(ctx, path, actor, status):
    """Post data package status transition actions."""
    status = constants.vault_package_state(status)
    actor = ctx.iiVaultGetActionActor(path, actor, '')['arguments'][2]

    if status is constants.vault_package_state.UNPUBLISHED:
        actor = "system"
        provenance.log_action(ctx, actor, path, "secured in vault")

    elif status is constants.vault_package_state.SUBMITTED_FOR_PUBLICATION:
        provenance.log_action(ctx, actor, path, "submitted for publication")

        # Store actor of submitted for pub;lication.
        vault.set_submitter(ctx, path, actor)

        if folder.datamanager_exists(ctx, path):
            # Send notifications to datamanagers.
            datamanagers = folder.get_datamanagers(ctx, path)
            message = "Data package submitted for publication"
            for datamanager in datamanagers:
                datamanager = '{}#{}'.format(*datamanager)
                notifications.set(ctx, actor, datamanager, path, message)

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
