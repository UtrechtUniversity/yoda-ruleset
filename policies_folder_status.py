# -*- coding: utf-8 -*-
"""Policy check functions for folder status transitions."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import folder
import meta
import notifications
import provenance
from util import *


def pre_status_transition(ctx, coll, current, new):
    """Action taken before status transition."""
    if current != constants.research_package_state.LOCKED \
        and new in [constants.research_package_state.LOCKED,
                    constants.research_package_state.SUBMITTED]:
        # Clear action log coming from SECURED state.
        # SECURED -> LOCKED and SECURED -> SUBMITTED
        if current is constants.research_package_state.SECURED:
            ctx.iiRemoveAVUs(coll, constants.UUORGMETADATAPREFIX + 'action_log')

        # Add locks to folder, descendants and ancestors
        x = ctx.iiFolderLockChange(coll, 'lock', '')
        if x['arguments'][2] != '0':
            return policy.fail('Could not lock folder')

    if new in [constants.research_package_state.FOLDER,
               constants.research_package_state.REJECTED,
               constants.research_package_state.SECURED]:
        # Clear action log coming from SECURED state.
        # SECURED -> FOLDER (backwards compatibility for v1.2 and older)
        if current is constants.research_package_state.SECURED:
            ctx.iiRemoveAVUs(coll, constants.UUORGMETADATAPREFIX + 'action_log')

        # Remove locks from folder, descendants and ancestors
        x = ctx.iiFolderLockChange(coll, 'unlock', '')
        if x['arguments'][2] != '0':
            return policy.fail('Could not lock folder')

    return policy.succeed()


def can_transition_folder_status(ctx, actor, coll, status_from, status_to):
    transition = (constants.research_package_state(status_from),
                  constants.research_package_state(status_to))
    if transition not in constants.folder_transitions:
        return policy.fail('Illegal status transition')

    meta_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    if status_to is constants.research_package_state.SUBMITTED:
        if not data_object.exists(ctx, meta_path):
            return policy.fail('Metadata missing, unable to submit this folder')

        if not meta.is_json_metadata_valid(ctx, meta_path):
            return policy.fail('Metadata is not valid, please open the metadata form for more information')

    elif status_to in [constants.research_package_state.ACCEPTED,
                       constants.research_package_state.REJECTED]:

        if pathutil.info(coll).space is pathutil.Space.RESEARCH:
            grp = pathutil.info(coll).group
            cat = group.get_category(ctx, grp)
            dmgrp = 'datamanager-' + cat

            if group.exists(ctx, dmgrp) and not user.is_member_of(ctx, dmgrp, actor):
                return policy.fail('Only a member of {} is allowed to accept or reject a submitted folder'.format(dmgrp))

    elif status_to is constants.research_package_state.SECURED:
        actor = user.user_and_zone(ctx)
        if not user.is_admin(ctx, actor):
            return policy.fail('Only a rodsadmin is allowed to secure a folder to the vault')

    return policy.succeed()


def can_set_folder_status_attr(ctx, actor, coll, status):
    try:
        new = constants.research_package_state(status)
    except ValueError:
        return policy.fail('New folder status attribute is invalid')

    current = folder.get_status(ctx, coll)

    x = can_transition_folder_status(ctx, actor, coll, current, new)
    if not x:
        return x
    else:
        return (current, new)


def post_status_transition(ctx, path, actor, status):
    """Post folder status transition actions."""
    status = constants.research_package_state(status)

    if status is constants.research_package_state.SUBMITTED:
        provenance.log_action(ctx, actor, path, "submitted for vault")

        # Store actor of submitted for vault.
        folder.set_submitter(ctx, path, actor)

        if pathutil.info(path).space is pathutil.Space.RESEARCH and folder.datamanager_exists(ctx, path):
            # Send notifications to datamanagers
            datamanagers = folder.get_datamanagers(ctx, path)
            message = "Data package submitted for the vault"
            for datamanager in datamanagers:
                datamanager = '{}#{}'.format(*datamanager)
                notifications.set(ctx, actor, datamanager, path, message)
        else:
            # Set status to accepted for deposit groups or if research group has no datamanager.
            folder.set_status(ctx, path, constants.research_package_state.ACCEPTED)

    elif status is constants.research_package_state.ACCEPTED:
        # Actor is system for deposit groups or if research group has no datamanager.
        if pathutil.info(path).space is pathutil.Space.DEPOSIT or not folder.datamanager_exists(ctx, path):
            actor = "system"

        provenance.log_action(ctx, actor, path, "accepted for vault")

        # Store actor of accepted for vault.
        folder.set_accepter(ctx, path, actor)

        # Send notifications to submitter.
        if pathutil.info(path).space is pathutil.Space.RESEARCH and folder.datamanager_exists(ctx, path):
            submitter = folder.get_submitter(ctx, path)
            message = "Data package accepted for vault"
            notifications.set(ctx, actor, submitter, path, message)

        # Set state to secure package in vault space.
        attribute = constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault"
        avu.set_on_coll(ctx, path, attribute, constants.CRONJOB_STATE['PENDING'])
        ctx.iiScheduleCopyToVault()

    elif status is constants.research_package_state.FOLDER:
        # If previous action was submit and new status is FOLDER action is unsubmit.
        provenance_log = provenance.get_provenance_log(ctx, path)
        if provenance_log[0][1] == "submitted for vault":
            provenance.log_action(ctx, actor, path, "unsubmitted for vault")
        else:
            provenance.log_action(ctx, actor, path, "unlocked")

    elif status is constants.research_package_state.LOCKED:
        provenance.log_action(ctx, actor, path, "locked")

    elif status is constants.research_package_state.REJECTED:
        provenance.log_action(ctx, actor, path, "rejected for vault")

        # Send notifications to submitter
        submitter = folder.get_submitter(ctx, path)
        message = "Data package rejected for vault"
        notifications.set(ctx, actor, submitter, path, message)

    elif status is constants.research_package_state.SECURED:
        actor = "system"
        provenance.log_action(ctx, actor, path, "secured in vault")

        # Send notifications to submitter and accepter
        data_package = folder.get_vault_data_package(ctx, path)
        submitter = folder.get_submitter(ctx, path)
        accepter = folder.get_accepter(ctx, path)
        message = "Data package secured in vault"
        notifications.set(ctx, actor, submitter, data_package, message)
        notifications.set(ctx, actor, accepter, data_package, message)

        # Handle vault packages from deposit module.
        if pathutil.info(path).space is pathutil.Space.DEPOSIT:
            # Grant submitter (depositor) read access to vault package.
            msi.set_acl(ctx, "recursive", "read", submitter, data_package)

            # Remove deposit folder after secure in vault.
            parent, _ = pathutil.chop(path)
            msi.set_acl(ctx, "default", "admin:write", user.full_name(ctx), parent)
            msi.set_acl(ctx, "recursive", "admin:own", user.full_name(ctx), path)
            collection.remove(ctx, path)
