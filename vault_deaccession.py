"""Functions to deaccession vault data packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from typing import List

import genquery

import admin
import constants
import folder
import groups
import policies_deaccession_status
import research
from util import *

__all__ = ['api_vault_deaccession_status',
           'api_vault_request_deaccession',
           'api_vault_cancel_deaccession',
           'api_vault_approve_deaccession',
           'rule_process_deaccession_status_transitions']


@api.make()
def api_vault_deaccession_status(ctx: rule.Context, coll: str) -> api.Result:
    """Request deaccession status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to request deaccession status from

    :returns: Vault data package deaccession status
    """
    return vault_deaccession_status(ctx, coll)


def vault_deaccession_status(ctx: rule.Context, coll: str) -> str:
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     f"COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.IIDEACCESSIONATTRNAME}'",
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return ""


@api.make()
def api_vault_request_deaccession(ctx: rule.Context, coll: str) -> api.Result:
    """Request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to deaccession

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_deaccession_status_transition(ctx, coll, constants.vault_deaccession_state.DEACCESSION_REQUESTED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_request_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_cancel_deaccession(ctx: rule.Context, coll: str) -> api.Result:
    """Cancel a request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to deaccession

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_deaccession_status_transition(ctx, coll, constants.vault_deaccession_state.ACTIVE)

    if ret[0] == '':
        log.write(ctx, 'api_vault_cancel_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_approve_deaccession(ctx: rule.Context, coll: str) -> api.Result:
    """Approve request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to deaccession

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_deaccession_status_transition(ctx, coll, constants.vault_deaccession_state.DEACCESSION_APPROVED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_approve_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


def set_deaccession_requester(ctx: rule.Context, path: str, actor: str) -> None:
    """Set submitter of data package deaccession request."""
    attribute = constants.UUORGMETADATAPREFIX + "deaccession_request_actor"
    try:
        avu.set_on_coll(ctx, path, attribute, actor)
    except msi.Error:
        log.write(ctx, "set_deaccession_requester: msiError - could not set deaccession requester AVU.")


def get_deaccession_requester(ctx: rule.Context, path: str) -> str:
    """Get submitter of data package deaccession request."""
    attribute = constants.UUORGMETADATAPREFIX + "deaccession_request_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_deaccession_approver(ctx: rule.Context, path: str, actor: str) -> None:
    """Set approver of data package deaccession request."""
    attribute = constants.UUORGMETADATAPREFIX + "deaccession_approval_actor"
    try:
        avu.set_on_coll(ctx, path, attribute, actor)
    except msi.Error:
        log.write(ctx, "set_deaccession_approver: msiError - could not set deaccession approver AVU.")


def get_deaccession_approver(ctx: rule.Context, path: str) -> str:
    """Get approver of data package deaccession request."""
    attribute = constants.UUORGMETADATAPREFIX + "deaccession_approval_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def get_deaccession_manifest(ctx: rule.Context, coll: str) -> api.Result:
    """Produce manifest with summary data for a deaccessioned data package.

    :param ctx: Combined type of a callback and rei struct
    :param coll: Parent collection of data objects to include

    :returns: Dict with number of files, total file size and checksum manifest
    """
    if not collection.exists(ctx, coll):
        return api.Error('nonexistent', 'The given path does not exist')

    # Validate the space type.
    space, _, _, _ = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return api.Error('invalidpath', 'The given path is not in a vault space')

    pre_summary = research.get_summary_manifest(ctx, coll)

    # TODO support adding custom deaccession reason
    return {
        "files": pre_summary['num_files'],
        "size": pre_summary['total_size'],
        "deaccession_complete": True,
        "deaccession_complete_reason": "This data package was deaccessioned."
    }


def is_transition_pending(ctx: rule.Context, coll_id: str) -> bool:
    """Check if data package has any status transition pending"""
    # Check if deaccession status transition is pending
    deaccession_status = f"{constants.UUORGMETADATAPREFIX}deaccession_status_action_{coll_id}"
    iter = genquery.row_iterator(
        "COLL_ID",
        "META_COLL_ATTR_NAME = '" + deaccession_status + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
        genquery.AS_LIST,
        ctx
    )
    for _row in iter:
        return True

    # Check if vault status transition is pending
    vault_status = f"{constants.UUORGMETADATAPREFIX}vault_status_action_{coll_id}"
    iter = genquery.row_iterator(
        "COLL_ID",
        "META_COLL_ATTR_NAME = '" + vault_status + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
        genquery.AS_LIST,
        ctx
    )
    for _row in iter:
        return True

    return False


def get_latest_actor(ctx: rule.Context, path: str) -> str | None:
    """
    Retrieve actor of latest deaccession action.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to vault data package

    :returns: Actor of latest deaccession action.
    """
    try:
        coll_id = collection.id_from_name(ctx, path)
        iter = list(genquery.Query(
                    ctx, "META_COLL_ATTR_VALUE",
                    f"META_COLL_ATTR_NAME = 'org_deaccession_action_{coll_id}'",
                    order_by="META_COLL_MODIFY_TIME desc",
                    output=genquery.AS_LIST, limit=1, parser=genquery.Parser.GENQUERY2))
        action = json.loads(iter[0][0])
        return action[2]
    except Exception:
        return None


def request_deaccession_status_transition(ctx: rule.Context, coll: str, new_status: constants.vault_deaccession_state) -> List:
    """Request vault deaccession status transition action.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault package to be changed of status in deaccession cycle
    :param new_status:       New deaccession status

    :return: List with status and statusinfo
    """
    # Gather info
    actor = user.full_name(ctx)
    coll_id = collection.id_from_name(ctx, coll)

    zone = user.zone(ctx)
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]
    category = groups.group_category(ctx, vault_group_name)

    is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))
    is_admin = admin.is_admin(ctx, user.name(ctx))

    # Determine group collection
    actor_group_path = '/' + zone + '/home/'
    if is_datamanager:
        actor_group_path += 'datamanager-' + category
    else:
        actor_group_path += folder.collection_group_name(ctx, coll)

    # Check permissions for status transitions
    if new_status == constants.vault_deaccession_state.DEACCESSION_REQUESTED:  # Only datamanager can request deaccession
        if not is_datamanager:
            log.write(ctx, "Deaccession request - User is not datamanager.")
            return ['PermissionDenied', 'Insufficient permissions: data package deaccession can only be requested by a datamanager.']
    elif new_status == constants.vault_deaccession_state.DEACCESSION_APPROVED:  # Only rodsadmin can approve deaccession
        if not is_admin:
            log.write(ctx, "Deaccession approval request - User is not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: approval of data package deaccession request can only be requested by a rodsadmin.']
    elif new_status == constants.vault_deaccession_state.DEACCESSION_COMPLETE:  # Deaccession is performed by system
        if not is_admin:
            log.write(ctx, "Deaccession process - User is not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: deaccession of data package can only be executed by a rodsadmin.']
    elif new_status == constants.vault_deaccession_state.ACTIVE:  # Cancellation of deaccession can be done by datamanager and technicaladmins only
        if not is_datamanager and not is_admin:
            log.write(ctx, "Deaccession cancel request - User is not datamanager and not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: cancellation of data package deaccession request can only be requested by a datamanager or a rodsadmin.']

    # Check if package is currently pending for another status transition
    if is_transition_pending(ctx, coll_id):
        return ['PermissionDenied', "A vault status transition is pending, please wait until it is finished."]

    # Check if transition is legal
    current_status = vault_deaccession_status(ctx, coll)
    is_legal = policies_deaccession_status.can_transition_deaccession_status(ctx, coll, current_status, new_status)
    if not is_legal:
        return ['PermissionDenied', 'Illegal status transition']

    # Attach action AVUs

    # TODO: technical admins have no access, grant temporary admin access?
    avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'deaccession_action_' + coll_id, jsonutil.dump([coll, new_status.value, actor]))
    avu.set_on_coll(ctx, actor_group_path, constants.UUORGMETADATAPREFIX + 'deaccession_status_action_' + coll_id, 'PENDING')

    return ['', '']


def process_deaccession_status_transition(ctx: rule.Context) -> None:
    """Process vault deaccession status transition action.

    :param ctx:              Combined type of a callback and rei struct
    """
    # Check user here is rods
    if user.name(ctx) != "rods":
        log.write(ctx, "process_deaccession_status_transition: Insufficient permissions - status transitions can only be performed by rods.")
        return

    # Scan for pending transitions
    action_iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}deaccession_action_%'",
        genquery.AS_LIST,
        ctx
    )

    for action_row in action_iter:
        # Initialize data
        data = jsonutil.parse(action_row[1])
        coll = data[0]
        coll_id = collection.id_from_name(ctx, coll)
        new_status = data[1]
        current_status = vault_deaccession_status(ctx, coll)
        actor = data[2]

        # Scan for pending status transitions
        status_iter = genquery.row_iterator(
            "COLL_NAME",
            f"META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}deaccession_status_action_{coll_id}' AND META_COLL_ATTR_VALUE = 'PENDING'",
            genquery.AS_LIST,
            ctx
        )

        for status_row in status_iter:
            # Check that transitions come from the same group collection
            if action_row[0] != status_row[0]:
                continue

            # Check current status in case transition already happened
            if new_status == current_status:
                continue

            # Check again if transition is legal
            is_legal = policies_deaccession_status.can_transition_deaccession_status(ctx, coll, constants.vault_deaccession_state(current_status), constants.vault_deaccession_state(new_status))
            if not is_legal:
                log.write(ctx, f"process_deaccession_status_transition: Illegal status transition from {current_status} to {new_status}.")
                continue
            else:
                # Set deaccession AVUs
                try:
                    if new_status == constants.vault_deaccession_state.ACTIVE.value:  # If deaccession has been denied or cancelled, remove AVU
                        avu.rm_from_coll(ctx, coll, constants.IIDEACCESSIONATTRNAME, current_status)
                    else:
                        avu.set_on_coll(ctx, coll, constants.IIDEACCESSIONATTRNAME, new_status)
                except msi.Error:
                    log.write(ctx, "process_deaccession_status_transition: msiError - Could not set deaccession AVUs.")
                    continue

                # Remove action AVUs (status only, action will be removed later)
                try:
                    avu.rm_from_coll(ctx, status_row[0], f"{constants.UUORGMETADATAPREFIX}deaccession_status_action_{coll_id}", "PENDING")
                except msi.Error:
                    log.write(ctx, "process_deaccession_status_transition: msiError - Could not remove action AVUs.")

    log.write(ctx, f"process_deaccession_status_transition: Successfully transitioned to {str(new_status)} by {actor} on {coll}")


@rule.make()
def rule_process_deaccession_status_transitions(ctx: rule.Context) -> None:
    """Rule interface for processing deaccession status transition request.

    :param ctx:              Combined type of a callback and rei struct
    """
    process_deaccession_status_transition(ctx)
