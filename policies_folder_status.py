"""Policy check functions for folder status transitions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

import folder
import meta
import notifications
import provenance
from metadata_utils import is_json_metadata_valid
from policies_utils import should_transition_submitted_to_accepted_immediately
from util import *


def pre_status_transition(ctx: rule.Context,
                          coll: str,
                          current: constants.research_package_state,
                          new: constants.research_package_state) -> policy.Succeed | policy.Fail:
    """Action taken before status transition."""
    if current != constants.research_package_state.LOCKED \
        and new in [constants.research_package_state.LOCKED,
                    constants.research_package_state.SUBMITTED]:
        # Backwards compatibility for folders that hold deprecated SECURED status.
        # Clear provenance log coming from SECURED or FOLDER state.
        # SECURED -> LOCKED and SECURED -> SUBMITTED
        # FOLDER -> LOCKED and FOLDER -> SUBMITTED
        if current in [constants.research_package_state.SECURED,
                       constants.research_package_state.FOLDER]:
            if not avu.rmw_from_coll(ctx, coll, f"{constants.UUORGMETADATAPREFIX}action_log", "%", catch=True):
                return policy.fail('Could not clear provenance log')

        # Add locks to folder, descendants and ancestors
        x = ctx.iiFolderLockChange(coll, 'lock', '')
        if x['arguments'][2] != '0':
            return policy.fail('Could not lock folder')

    if new in [constants.research_package_state.FOLDER,
               constants.research_package_state.REJECTED,
               constants.research_package_state.SECURED]:
        # Backwards compatibility for folders that hold deprecated SECURED status.
        # Clear provenance log coming from SECURED state.
        # SECURED -> FOLDER
        if current is constants.research_package_state.SECURED:
            if not avu.rmw_from_coll(ctx, coll, f"{constants.UUORGMETADATAPREFIX}action_log", "%", catch=True):
                return policy.fail('Could not clear provenance log')

        # Remove locks from folder, descendants and ancestors
        x = ctx.iiFolderLockChange(coll, 'unlock', '')
        if x['arguments'][2] != '0':
            return policy.fail('Could not unlock folder')

    return policy.succeed()


def can_transition_folder_status(ctx: rule.Context,
                                 actor: str,
                                 coll: str,
                                 status_from: str,
                                 status_to: str) -> policy.Succeed | policy.Fail:
    transition = (constants.research_package_state(status_from),
                  constants.research_package_state(status_to))
    if transition not in constants.folder_transitions:
        # YDA-6337: Users sometimes try to resubmit a collection.
        # In both research and deposit, it is helpful to show that a package has already been submitted
        # if it is in the 'submitted' or 'accepted' state. Note that in deposit, the package typically
        # stays in the 'submitted' state only briefly, since the system accepts it automatically
        # without requiring a data manager.
        if (status_from in [constants.research_package_state.SUBMITTED, constants.research_package_state.ACCEPTED]
                and status_to is constants.research_package_state.SUBMITTED):
            return policy.fail('This data package has already been submitted')
        return policy.fail('Illegal status transition')

    meta_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    if status_to is constants.research_package_state.SUBMITTED:
        if not data_object.exists(ctx, meta_path):
            return policy.fail('Metadata missing, unable to submit this folder')

        if not is_json_metadata_valid(ctx, meta_path):
            return policy.fail('Metadata is incomplete or invalid, please open the metadata form for more information')

    elif status_to in [constants.research_package_state.ACCEPTED,
                       constants.research_package_state.REJECTED]:

        space, _, grp, _ = pathutil.info(coll)
        if space is pathutil.Space.RESEARCH:
            cat = group.get_category(ctx, grp)
            dmgrp = 'datamanager-' + cat

            if group.exists(ctx, dmgrp) and not user.is_member_of(ctx, dmgrp, actor):
                return policy.fail('Only a member of {} is allowed to accept or reject a submitted folder'.format(dmgrp))

    elif status_from is constants.research_package_state.ACCEPTED and status_to is constants.research_package_state.FOLDER:
        actor = user.user_and_zone(ctx)
        if not user.is_rodsadmin(ctx, actor):
            return policy.fail('Only a rodsadmin is allowed to secure a folder to the vault')

    return policy.succeed()


def can_set_folder_status_attr(ctx: rule.Context,
                               actor: str,
                               coll: str,
                               status: str) -> policy.Succeed | policy.Fail:
    try:
        status = "" if status == "FOLDER" else status
        new = constants.research_package_state(status)
    except ValueError:
        return policy.fail('New folder status attribute is invalid')

    current = folder.get_status(ctx, coll)

    x = can_transition_folder_status(ctx, actor, coll, current, new)
    if not x:
        return x
    else:
        return (current, new)


def post_status_transition(ctx: rule.Context,
                           path: str,
                           actor: str,
                           status: str) -> None:
    """Post folder status transition actions."""
    status = "" if status == "FOLDER" else status
    status = constants.research_package_state(status)
    space, _, group, subpath = pathutil.info(path)

    if status is constants.research_package_state.SUBMITTED:
        provenance.log_action(ctx, actor, path, "submitted for vault")

        # Store actor of submitted for vault.
        folder.set_submitter(ctx, path, actor)

        if space is pathutil.Space.RESEARCH:
            try:
                datamanagers = folder.get_datamanagers(ctx, path)
            except ValueError as e:
                log.write(ctx, f"Unable to send submitted to vault notifications for <{path}>: cannot get data managers: {str(e)}")
                datamanagers = []

            # Send notifications to datamanagers
            message = "Data package submitted for the vault"
            for datamanager in datamanagers:
                datamanager_name = '{}#{}'.format(*datamanager)
                notifications.set(ctx, actor, datamanager_name, path, message)
        else:
            datamanagers = []

        if should_transition_submitted_to_accepted_immediately(path, datamanagers):
            folder.set_status(ctx, path, constants.research_package_state.ACCEPTED)

    elif status is constants.research_package_state.ACCEPTED:
        # Actor is system for deposit groups or if research group has no datamanager.
        try:
            datamanager_exists = folder.get_datamanager_coll(ctx, path) is not None
        except ValueError as e:
            log.write(ctx, f"Unable to determine whether <{path}> has data managers: {str(e)}")
            datamanager_exists = False

        if space is pathutil.Space.DEPOSIT or not datamanager_exists:
            actor = "system"

        # Log action at least one second after previous action, to ensure correct order of provenance log.
        time.sleep(1)
        provenance.log_action(ctx, actor, path, "accepted for vault")

        # Store actor of accepted for vault.
        folder.set_accepter(ctx, path, actor)

        # Send notifications to submitter.
        if space is pathutil.Space.RESEARCH and datamanager_exists:
            submitter = folder.get_submitter(ctx, path)
            message = "Data package accepted for vault"
            notifications.set(ctx, actor, submitter, path, message)

        # Set state to tell copytovault to secure package in vault space.
        attribute = constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault"
        avu.set_on_coll(ctx, path, attribute, constants.CRONJOB_STATE['PENDING'])

    elif status is constants.research_package_state.FOLDER:
        # If previous action was submit and new status is FOLDER action is unsubmit.
        provenance_log = provenance.get_provenance_log(ctx, path)
        if provenance_log[0][1] == "submitted for vault":
            provenance.log_action(ctx, actor, path, "unsubmitted for vault")
        elif provenance_log[0][1] == "accepted for vault":
            actor = "system"
            provenance.log_action(ctx, actor, path, "secured in vault")

            # Send notifications to submitter and accepter
            data_package = folder.get_vault_data_package(ctx, path)
            submitter = folder.get_submitter(ctx, path)
            accepter = folder.get_accepter(ctx, path)
            message = "Data package secured in vault"
            notifications.set(ctx, actor, submitter, data_package, message)
            notifications.set(ctx, actor, accepter, data_package, message)

            # Check if user requested to delete research space copy.
            delete_research_copy = False
            if space is pathutil.Space.RESEARCH:
                try:
                    research_coll = avu.get_attr_val_of_coll(ctx, path, constants.DELETE_RESEARCH_COPY)
                    delete_research_copy = research_coll == path
                except ValueError:
                    # AVU DELETE_RESEARCH_COPY is absent, so copy in research remains.
                    pass

            # Handle vault packages from deposit module.
            if space is pathutil.Space.DEPOSIT:
                # Grant submitter (depositor) read access to vault package.
                msi.set_acl(ctx, "recursive", "read", submitter, data_package)

                # Retrieve Data Access Restriction of vault package.
                meta_path = meta.get_collection_metadata_path(ctx, path)
                open_package = False
                if meta_path is not None:
                    metadata = jsonutil.read(ctx, meta_path)
                    data_access_restriction = metadata.get("Data_Access_Restriction", "")
                    if data_access_restriction == "Open - freely retrievable":
                        open_package = True

                # Revoke read access for research group when data package is not open.
                if not open_package:
                    msi.set_acl(ctx, "recursive", "null", group, data_package)

            # Delete research package or deposit folder if needed.
            if space is pathutil.Space.DEPOSIT or delete_research_copy:
                parent, _ = pathutil.chop(path)
                admin = user.full_name(ctx)
                msi.set_acl(ctx, "default",  "admin:write", admin, parent)
                msi.set_acl(ctx, "recursive", "admin:own",  admin, path)
                if space is pathutil.Space.RESEARCH and not subpath:
                    collection.empty(ctx, path)
                else:
                    collection.remove(ctx, path)
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
