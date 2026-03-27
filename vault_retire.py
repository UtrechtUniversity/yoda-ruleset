"""Functions to retire vault data packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List

import genquery

import constants
import folder
import groups
import policies_retirement_status
from util import *

__all__ = ['api_vault_retirement_status',
           'api_vault_request_retirement',
           'api_vault_cancel_retirement',
           'api_vault_approve_retirement',
           'rule_process_retirement_status_transitions']


@api.make()
def api_vault_retirement_status(ctx: rule.Context, coll: str) -> api.Result:
    """Request retirement status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to request retirement status from

    :returns: Vault data package retirement status
    """
    return vault_retirement_status(ctx, coll)


def vault_retirement_status(ctx: rule.Context, coll: str) -> str:
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     f"COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.IIRETIREATTRNAME}'",
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return ""


@api.make()
def api_vault_request_retirement(ctx: rule.Context, coll: str) -> api.Result:
    """Request to retire a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to retire

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.RETIREMENT_REQUESTED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_request_retirement: iiAdminVaultRetire')
        ctx.iiAdminVaultRetire()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_cancel_retirement(ctx: rule.Context, coll: str) -> api.Result:
    """Cancel a request to retire a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to retire

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.ACTIVE)

    if ret[0] == '':
        log.write(ctx, 'api_vault_cancel_retirement: iiAdminVaultRetire')
        ctx.iiAdminVaultRetire()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_approve_retirement(ctx: rule.Context, coll: str) -> api.Result:
    """Approve request to retire a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to retire

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.RETIREMENT_APPROVED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_approve_retirement: iiAdminVaultRetire')
        ctx.iiAdminVaultRetire()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


def set_retirement_requester(ctx: rule.Context, path: str, actor: str) -> None:
    """Set submitter of data package retirement request."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_request_actor"
    try:
        avu.set_on_coll(ctx, path, attribute, actor)
    except msi.Error:
        log.write(ctx, "set_retirement_requester: msiError - could not set retirement requester AVU.")


def get_retirement_requester(ctx: rule.Context, path: str) -> str:
    """Get submitter of data package retirement request."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_request_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_retirement_approver(ctx: rule.Context, path: str, actor: str) -> None:
    """Set approver of data package retirement request."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_approval_actor"
    try:
        avu.set_on_coll(ctx, path, attribute, actor)
    except msi.Error:
        log.write(ctx, "set_retirement_approver: msiError - could not set retirement approver AVU.")


def get_retirement_approver(ctx: rule.Context, path: str) -> str:
    """Get approver of data package retirement request."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_approval_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def is_transition_pending(ctx: rule.Context, coll_id: str) -> bool:
    """Check if data package has any status transition pending"""
    # Check if retirement status transition is pending
    retirement_status = f"{constants.UUORGMETADATAPREFIX}retirement_status_action_{coll_id}"
    iter = genquery.row_iterator(
        "COLL_ID",
        "META_COLL_ATTR_NAME = '" + retirement_status + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
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


def request_retirement_status_transition(ctx: rule.Context, coll: str, new_status: constants.vault_retirement_state) -> List:
    """Request vault retirement status transition action.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault package to be changed of status in retirement cycle
    :param new_status:       New retirement status

    :return: List with status and statusinfo
    """
    # Gather info
    actor = user.full_name(ctx)
    coll_id = collection.id_from_name(ctx, coll)

    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]
    category = groups.group_category(ctx, vault_group_name)
    zone = user.zone(ctx)
    actor_group_path = '/' + zone + '/home/datamanager-' + category

    # Check permissions for status transitions
    if new_status == constants.vault_retirement_state.RETIREMENT_REQUESTED:  # Only datamanager can request retirement
        is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))
        if not is_datamanager:
            log.write(ctx, "Retirement request - User is not datamanager.")
            return ['PermissionDenied', 'Insufficient permissions: data package retirement can only be requested by a datamanager.']
    elif new_status == constants.vault_retirement_state.RETIREMENT_APPROVED:  # Only rodsadmin can approve retirement
        if user.user_type(ctx) != 'rodsadmin':
            log.write(ctx, "Retirement approval request - User is not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: approval of data package retirement request can only be requested by a rodsadmin.']
    elif new_status == constants.vault_retirement_state.RETIRED:  # Retirement is performed by system
        if user.user_type(ctx) != 'rodsadmin':
            log.write(ctx, "Retirement process - User is not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: retirement of data package can only be executed by a rodsadmin.']
    elif new_status == constants.vault_retirement_state.ACTIVE:  # Cancellation of retirement can be done by datamanager and technicaladmins only
        is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))
        if not is_datamanager and user.user_type(ctx) != 'rodsadmin':
            log.write(ctx, "Retirement cancel request - User is not datamanager and not rodsadmin.")
            return ['PermissionDenied', 'Insufficient permissions: cancellation of data package retirement request can only be requested by a datamanager or a rodsadmin.']

    # Check if package is currently pending for another status transition
    if is_transition_pending(ctx, coll_id):
        return ['PermissionDenied', "A vault status transition is pending, please wait until it is finished."]

    # Check if transition is legal
    current_status = vault_retirement_status(ctx, coll)
    is_legal = policies_retirement_status.can_transition_retirement_status(ctx, coll, current_status, new_status)
    if not is_legal:
        return ['PermissionDenied', 'Illegal status transition']

    # Attach action AVUs
    try:
        avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'retirement_action_' + coll_id, jsonutil.dump([coll, new_status.value, actor]))
        avu.set_on_coll(ctx, actor_group_path, constants.UUORGMETADATAPREFIX + 'retirement_status_action_' + coll_id, 'PENDING')
    except msi.Error:
        return ['InternalError', 'Something went wrong with the request']

    return ['', '']


def process_retirement_status_transition(ctx: rule.Context) -> None:
    """Process vault retirement status transition action.

    :param ctx:              Combined type of a callback and rei struct
    """
    # Check user here is rods
    if user.name(ctx) != "rods":
        log.write(ctx, "process_retirement_status_transition: Insufficient permissions - status transitions can only be performed by rods.")
        return

    # Scan for pending transitions
    action_iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}retirement_action_%'",
        genquery.AS_LIST,
        ctx
    )

    for action_row in action_iter:
        # Initialize data
        data = jsonutil.parse(action_row[1])
        coll = data[0]
        coll_id = collection.id_from_name(ctx, coll)
        new_status = data[1]
        current_status = vault_retirement_status(ctx, coll)
        actor = data[2]

        # Scan for pending status transitions
        status_iter = genquery.row_iterator(
            "COLL_NAME",
            f"META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}retirement_status_action_{coll_id}' AND META_COLL_ATTR_VALUE = 'PENDING'",
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
            is_legal = policies_retirement_status.can_transition_retirement_status(ctx, coll, constants.vault_retirement_state(current_status), constants.vault_retirement_state(new_status))
            if not is_legal:
                log.write(ctx, f"process_retirement_status_transition: Illegal status transition from {current_status} to {new_status}.")
                continue
            else:
                # Set retirement AVUs
                try:
                    if new_status == constants.vault_retirement_state.ACTIVE.value:  # If retirement has been denied or cancelled, remove AVU
                        avu.rm_from_coll(ctx, coll, constants.IIRETIREATTRNAME, current_status)
                    else:
                        avu.set_on_coll(ctx, coll, constants.IIRETIREATTRNAME, new_status)
                except msi.Error:
                    log.write(ctx, "process_retirement_status_transition: msiError - Could not set retirement AVUs.")
                    continue

                # Remove action AVUs (status only, action will be removed later)
                try:
                    avu.rm_from_coll(ctx, status_row[0], f"{constants.UUORGMETADATAPREFIX}retirement_status_action_{coll_id}", "PENDING")
                except msi.Error:
                    log.write(ctx, "process_retirement_status_transition: msiError - Could not remove action AVUs.")

    log.write(ctx, f"process_retirement_status_transition: Successfully transitioned to {str(new_status)} by {actor} on {coll}")


@rule.make()
def rule_process_retirement_status_transitions(ctx: rule.Context) -> None:
    """Rule interface for processing retirement status transition request.

    :param ctx:              Combined type of a callback and rei struct
    """
    process_retirement_status_transition(ctx)
