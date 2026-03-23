"""Functions to retire vault data packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

import constants
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
    # check collection is in vault
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    # check valid status transition
    # update provenance log
    # notify technical admin
    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.RETIREMENT_REQUESTED)

    # update status
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
    # check collection is in vault
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    # check valid status transition
    # update provenance log
    # notify datamanager / technicaladmin
    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.ACTIVE)

    # update status
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
    # check collection is in vault
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    # check valid status transition
    # update provenance log
    # notify datamanager
    ret = request_retirement_status_transition(ctx, coll, constants.vault_retirement_state.RETIREMENT_APPROVED)

    # update status
    if ret[0] == '':
        log.write(ctx, 'api_vault_approve_retirement: iiAdminVaultRetire')
        ctx.iiAdminVaultRetire()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


def set_requester(ctx: rule.Context, path: str, actor: str) -> None:
    """Set submitter of data package for retirement."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_request_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_requester(ctx: rule.Context, path: str) -> str:
    """Get submitter of data package for retirement."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_request_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_approver(ctx: rule.Context, path: str, actor: str) -> None:
    """Set approver of data package for retirement."""
    attribute = constants.UUORGMETADATAPREFIX + "retirement_approval_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_approver(ctx: rule.Context, path: str) -> str:
    """Get approver of data package for retirement."""
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


def request_retirement_status_transition(ctx: rule.Context, coll: str, new_status: str) -> List:
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
            return ['PermissionDenied', 'Insufficient permissions: package retirement can only be requested by a datamanager.']
    elif new_status == constants.vault_retirement_state.RETIREMENT_APPROVED:  # Only rodsadmin can approve retirement
        if user.user_type(ctx) != 'rodsadmin':
            log.write(ctx, "Retirement approval request - User is not rodsadmin")
            return ['PermissionDenied', 'Insufficient permissions: retirement status transition to approved can only be requested by a rodsadmin.']
    elif new_status == constants.vault_retirement_state.RETIRED:  # Retirement is performed by system
        if user.user_type(ctx) != 'rodsadmin':
            log.write(ctx, "Retirement request - User is not rodsadmin")
            return ['PermissionDenied', 'Insufficient permissions: retirement status transition to retired can only be requested by a rodsadmin.']

    # Check if package is currently pending for another status transition
    if is_transition_pending(ctx, coll_id):
        return ['PermissionDenied', "A vault status transition is pending, please wait until it is finished."]

    # Check if transition is legal
    current_status = vault_retirement_status(ctx, coll)
    is_legal = policies_retirement_status.can_transition_retirement_status(ctx, coll, current_status, new_status)
    if not is_legal:
        return ['PermissionDenied', 'Illegal status transition']

    # Attach action AVUs
    avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'retirement_action_' + coll_id, jsonutil.dump([coll, str(new_status), actor]))
    avu.set_on_coll(ctx, actor_group_path, constants.UUORGMETADATAPREFIX + 'retirement_status_action_' + coll_id, 'PENDING')

    return ['', '']


def process_retirement_status_transition(ctx: rule.Context) -> None:
    """Process vault retirement status transition action.

    :param ctx:              Combined type of a callback and rei struct
    """
    # Check user here is rods
    if user.name(ctx) != "rods":
        log.write(ctx, "Error in process_retirement_status_transition: Insufficient permissions - status transitions can only be performed by rods.")

    # Scan for pending actions
    action_iter = genquery.row_iterator(
        "COLL_NAME, COLL_ID",
        f"META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}retirement_action_%'",
        genquery.AS_LIST,
        ctx
    )
    if len(list(action_iter)) < 1:
        log.write(ctx, "Error in process_retirement_status_transition: no folder with pending actions found. Ignoring...")

    for row in action_iter:
        coll_id = row[1]

        log.write(ctx, f"action_iter_row: {row}")

        # Scan for pending status transitions
        status_iter = genquery.row_iterator(
            "COLL_NAME, COLL_ID",
            f"META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}retirement_status_action_{coll_id}' AND META_COLL_ATTR_VALUE = 'PENDING'",
            genquery.AS_LIST,
            ctx
        )

    # TODO: pick up new status and actor from AVU

    # TODO: check current status in case transition already happened

    # TODO: assign AVUs (status, requester actor, approval actor if any)


@rule.make()
def rule_process_retirement_status_transitions(ctx: rule.Context) -> None:
    """Rule interface for processing retirement status transition request.

    :param ctx:              Combined type of a callback and rei struct
    """
    process_retirement_status_transition(ctx)
