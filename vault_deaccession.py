"""Functions to deaccession vault data packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from datetime import date, datetime
from typing import List

import genquery
from dateutil.relativedelta import relativedelta

import admin
import constants
import folder
import groups
import policies_deaccession_status
import publication
import research
import vault
from util import *

__all__ = ['api_vault_deaccession_status',
           'api_vault_request_deaccession',
           'api_vault_cancel_deaccession',
           'api_vault_approve_deaccession',
           'rule_process_deaccession_status_transitions',
           'rule_pending_deaccession_deletion']

DEACCESSION_REASON_ATTRNAME = constants.UUORGMETADATAPREFIX + 'deaccession_reason'
DEACCESSION_REQUESTACTOR_ATTRNAME = constants.UUORGMETADATAPREFIX + "deaccession_request_actor"
DEACCESSION_APPROVALACTOR_ATTRNAME = constants.UUORGMETADATAPREFIX + "deaccession_approval_actor"
DEACCESSION_CANCELATIONACTOR_ATTRNAME = constants.UUORGMETADATAPREFIX + "deaccession_cancelation_actor"
DEACCESSION_MANIFEST_FILE = 'deaccession-manifest.json'


# Deaccession utils {{{
def get_deaccession_reason(ctx: rule.Context, coll: str) -> str:
    """Get reason for deaccession of data package.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession

    :returns:   Reason for deaccession as string
    """
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     f"COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{DEACCESSION_REASON_ATTRNAME}'",
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return ""


def get_deaccession_actor(ctx: rule.Context, coll: str, action: str) -> str:
    """Get actor of data package deaccession action.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession
    :param action:  Deaccession action that actor performed (request, approval, cancelation)

    :returns:   Deaccession action's actor as string
    """
    attribute = constants.UUORGMETADATAPREFIX + f"deaccession_{action}_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, coll))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def get_deaccession_date(ctx: rule.Context, vault_package: str) -> datetime | None:
    """Determine the time of deaccession as a datetime with UTC offset.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :return: Deaccession date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[1])
        if log_item_list[1] == "deaccessioned":
            return datetime.fromtimestamp(int(log_item_list[0]))

    return None
# }}}


# Deaccession status API {{{
@api.make()
def api_vault_deaccession_status(ctx: rule.Context, coll: str) -> api.Result:
    """Request deaccession status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault data package to request deaccession status from

    :returns: API result
    """
    return vault_deaccession_status(ctx, coll)


def vault_deaccession_status(ctx: rule.Context, coll: str) -> str:
    """Request deaccession status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault data package to request deaccession status from

    :returns: Vault data package deaccession status as string
    """
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     f"COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.IIDEACCESSIONSTATUSATTRNAME}'",
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return ""


@api.make()
def api_vault_request_deaccession(ctx: rule.Context, coll: str, reason: str) -> api.Result:
    """Request to deaccession a vault data package.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package to deaccession
    :param reason:  Reason for reaccession of vault data package

    :returns: API result
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    new_status = constants.vault_deaccession_state.DEACCESSION_REQUESTED
    ret = request_deaccession_status_transition(ctx, coll, new_status, reason)

    if ret[0] == '':
        log.write(ctx, 'api_vault_request_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession(coll, new_status.value)
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_cancel_deaccession(ctx: rule.Context, coll: str) -> api.Result:
    """Cancel a request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault data package to cancel deaccession from

    :returns: API result
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    new_status = constants.vault_deaccession_state.ACTIVE
    ret = request_deaccession_status_transition(ctx, coll, new_status)

    if ret[0] == '':
        log.write(ctx, 'api_vault_cancel_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession(coll, new_status.value)
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_approve_deaccession(ctx: rule.Context, coll: str) -> api.Result:
    """Approve request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault data package to approve deaccession on

    :returns: API result
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    new_status = constants.vault_deaccession_state.DEACCESSION_APPROVED
    ret = request_deaccession_status_transition(ctx, coll, new_status)

    if ret[0] == '':
        log.write(ctx, 'api_vault_approve_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession(coll, new_status.value)
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


def vault_complete_deaccession(ctx: rule.Context, coll: str) -> None:
    """Approve request to deaccession a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault data package to approve deaccession on
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        log.write(ctx, "api_vault_approve_deaccession: Invalid vault path")

    new_status = constants.vault_deaccession_state.DEACCESSION_COMPLETE
    ret = request_deaccession_status_transition(ctx, coll, new_status)

    if ret[0] == '':
        log.write(ctx, 'api_vault_approve_deaccession: iiAdminVaultDeaccession')
        ctx.iiAdminVaultDeaccession(coll, new_status.value)
    else:
        log.write(ctx, f"api_vault_approve_deaccession: Failed to complete deaccession on package '{coll}'")
# }}}


# Deaccession status transitions {{{
def set_temp_deaccession_reason(ctx: rule.Context, actor_group_path: str, path: str, reason: str) -> bool:
    """Set deaccession reason temporarily on actor group path.

    :param ctx:                 Combined type of a callback and rei struct
    :param actor_group_path:    Group collection of actor
    :param path:                Vault data package in deaccession
    :param reason:              Reason for deaccession

    :returns:   True if successfully set, otherwise False
    """
    try:
        avu.set_on_coll(ctx, actor_group_path, DEACCESSION_REASON_ATTRNAME, jsonutil.dump([path, reason]))
    except msi.Error:
        return False

    return True


def set_deaccession_reason(ctx: rule.Context, coll: str, actor: str) -> bool:
    """Retrieve and set deaccession reason on data package that is being deaccessioned.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession
    :param actor:   Actor of deaccession action (request)

    :returns:   True if successfully set, otherwise False
    """
    # Retrieve datamanager group collection
    coll_parts = coll.split('/')
    zone = coll_parts[1]
    vault_group_name = coll_parts[3]
    category = groups.group_category(ctx, vault_group_name)
    is_datamanager = groups.user_is_datamanager(ctx, category, actor)
    if not is_datamanager:
        log.write(ctx, f"set_deaccession_reason: Current actor '{actor}' is not datamanager of collection '{coll}'.")
        return False
    dm_group_coll = f"/{zone}/home/datamanager-{category}"

    # Retrieve deaccession reason from datamanager group collection
    reason_data = list(genquery.Query(ctx,
                                      'META_COLL_ATTR_VALUE',
                                      f"COLL_NAME = '{dm_group_coll}' AND META_COLL_ATTR_NAME = '{DEACCESSION_REASON_ATTRNAME}' AND META_COLL_ATTR_VALUE like '%{coll}%'",
                                      offset=0, limit=1, output=genquery.AS_LIST))[0][0]
    reason_json = jsonutil.parse(reason_data)
    reason = reason_json[1]

    # Set deaccession reason to data package that is being deaccessioned
    try:
        avu.set_on_coll(ctx, coll, DEACCESSION_REASON_ATTRNAME, reason)
    except msi.Error:
        return False

    try:
        avu.rm_from_coll(ctx, dm_group_coll, DEACCESSION_REASON_ATTRNAME, reason_data)
    except msi.Error:
        log.write(ctx, "set_deaccession_reason: Could not clean up temporary deaccession reason AVU from datamanager group collection. Ignoring...")

    return True


def is_transition_pending(ctx: rule.Context, coll_id: str) -> bool:
    """Check if data package has any status transition pending.

    :param ctx:     Combined type of a callback and rei struct
    :param coll_id: ID of vault data package in deaccession

    :returns:   True if a transition is pending, otherwise False
    """
    # Check if vault status transition is pending
    vault_status = f"{constants.UUORGMETADATAPREFIX}vault_status_action_{coll_id}"
    iter = genquery.row_iterator(
        "COLL_ID",
        f"META_COLL_ATTR_NAME = '{vault_status}' AND META_COLL_ATTR_VALUE = 'PENDING'",
        genquery.AS_LIST,
        ctx
    )
    for _row in iter:
        return True

    return False


def cleanup_deaccession_cancel(ctx: rule.Context, coll: str) -> None:
    """Cleanup deaccession AVUs after cancellation.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession
    """
    try:
        # Cleanup requester AVU if any
        requester = get_deaccession_actor(ctx, coll, "request")
        if requester != "":
            avu.rm_from_coll(ctx, coll, DEACCESSION_REQUESTACTOR_ATTRNAME, requester)

        # Cleanup reason AVU
        reason = get_deaccession_reason(ctx, coll)
        if reason != "":
            avu.rm_from_coll(ctx, coll, DEACCESSION_REASON_ATTRNAME, reason)
    except msi.Error:
        log.write(ctx, "deaccession_cancel_cleanup: Could not clean up deaccession AVUs.")


def request_deaccession_status_transition(ctx: rule.Context, coll: str, new_status: constants.vault_deaccession_state, reason: str | None = None) -> List:
    """Request vault deaccession status transition action.

    :param ctx:         Combined type of a callback and rei struct
    :param coll:        Vault package to be changed of status in deaccession cycle
    :param new_status:  New deaccession status
    :param reason:      Reason for reaccession of vault data package (when requesting), otherwise none

    :return: List with status and statusinfo
    """
    # Gather info
    zone = user.zone(ctx)
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]
    category = groups.group_category(ctx, vault_group_name)

    is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))
    is_admin = admin.is_admin(ctx, user.name(ctx))

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

    # For deaccession request, add reason for deaccession
    if new_status == constants.vault_deaccession_state.DEACCESSION_REQUESTED:
        dm_group_coll = f"/{zone}/home/datamanager-{category}"
        if not reason or (reason and not set_temp_deaccession_reason(ctx, dm_group_coll, coll, reason)):
            log.write(ctx, "Deaccession request - Could not set reason for deaccession.")
            return ['InternalError', 'Something went wrong: could not set reason for deaccession.']

    # Check if package is currently pending for another status transition
    coll_id = collection.id_from_name(ctx, coll)
    if is_transition_pending(ctx, coll_id):
        return ['PermissionDenied', "A vault status transition is pending, please wait until it is finished."]

    # Check if transition is legal
    current_status = vault_deaccession_status(ctx, coll)
    is_legal = policies_deaccession_status.can_transition_deaccession_status(ctx, coll, current_status, new_status)
    if not is_legal:
        return ['PermissionDenied', 'Illegal status transition']

    return ['', '']


def process_deaccession_status_transition(ctx: rule.Context, actor: str, coll: str, new_status: str) -> None:
    """Process vault deaccession status transition action.

    :param ctx:              Combined type of a callback and rei struct
    :param actor:            User who initiated the deaccession status transition
    :param coll:             Vault package to be changed of status in deaccession cycle
    :param new_status:       New deaccession status
    """
    # Check user here is rods
    if user.name(ctx) != "rods":
        log.write(ctx, "process_deaccession_status_transition: Insufficient permissions - status transitions can only be performed by rods.")
        return

    # Check current status in case transition already happened
    current_status = vault_deaccession_status(ctx, coll)
    if new_status == current_status:
        return

    # Check again if transition is legal
    is_legal = policies_deaccession_status.can_transition_deaccession_status(ctx, coll, constants.vault_deaccession_state(current_status), constants.vault_deaccession_state(new_status))
    if not is_legal:
        log.write(ctx, f"process_deaccession_status_transition: Illegal status transition from {current_status} to {new_status}.")
        return

    # Check if package is being resubmitted for deaccession (remove cancelation actor if any)
    if current_status == constants.vault_deaccession_state.ACTIVE.value:
        cancel_actor = get_deaccession_actor(ctx, coll, "cancelation")
        if cancel_actor != "":
            avu.rm_from_coll(ctx, coll, DEACCESSION_CANCELATIONACTOR_ATTRNAME, cancel_actor)

    # Apply actor AVU
    try:
        if constants.vault_deaccession_state(new_status) == constants.vault_deaccession_state.DEACCESSION_REQUESTED:
            avu.set_on_coll(ctx, coll, DEACCESSION_REQUESTACTOR_ATTRNAME, actor)
        elif constants.vault_deaccession_state(new_status) == constants.vault_deaccession_state.DEACCESSION_APPROVED:
            avu.set_on_coll(ctx, coll, DEACCESSION_APPROVALACTOR_ATTRNAME, actor)
        elif constants.vault_deaccession_state(new_status) == constants.vault_deaccession_state.ACTIVE:
            avu.set_on_coll(ctx, coll, DEACCESSION_CANCELATIONACTOR_ATTRNAME, actor)
    except msi.Error:
        log.write(ctx, "process_deaccession_status_transition: Could not set deaccession actor AVUs.")

    # Apply reason AVU
    if constants.vault_deaccession_state(new_status) == constants.vault_deaccession_state.DEACCESSION_REQUESTED:
        if not set_deaccession_reason(ctx, coll, actor):
            log.write(ctx, "process_deaccession_status_transition: Could not set deaccession reason AVU.")
            return

    # Apply status AVU
    try:
        if constants.vault_deaccession_state(new_status) == constants.vault_deaccession_state.ACTIVE:  # If deaccession has been denied or cancelled, remove AVU
            avu.rm_from_coll(ctx, coll, constants.IIDEACCESSIONSTATUSATTRNAME, current_status)
        else:
            avu.set_on_coll(ctx, coll, constants.IIDEACCESSIONSTATUSATTRNAME, new_status)
    except msi.Error:
        log.write(ctx, "process_deaccession_status_transition: Could not set deaccession status AVUs.")
        return

    log.write(ctx, f"process_deaccession_status_transition: Successfully transitioned to {str(new_status)} by {actor} on {coll}")


@rule.make()
def rule_process_deaccession_status_transitions(ctx: rule.Context, actor: str, coll: str, new_status: str) -> None:
    """Rule interface for processing deaccession status transition request.

    :param ctx:              Combined type of a callback and rei struct
    :param actor:            User who initiated the deaccession status transition
    :param coll:             Vault package to be changed of status in deaccession cycle
    :param new_status:       New deaccession status
    """
    process_deaccession_status_transition(ctx, actor, coll, new_status)
# }}}


# Deaccession processing {{{
def generate_deaccession_manifest(ctx: rule.Context, coll: str) -> str:
    """Produce manifest with summary data for a deaccessioned data package.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession

    :returns: Error string, if any
    """
    if not collection.exists(ctx, coll):
        return "The given path does not exist."

    # Validate the space type
    space, _, _, _ = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return "The given path is not in a vault space."

    # Get summary manifest
    original_path = f"{coll}/original"
    pre_manifest = research.research_manifest(ctx, original_path)
    manifest = {
        "num_files": pre_manifest['files'],
        "num_checksums": pre_manifest['checksums'],
        "size": pre_manifest['size'],
        "checksums": pre_manifest['manifest'],
        "reason": get_deaccession_reason(ctx, coll)
    }

    # Write manifest file to data package
    manifest_path = f"{coll}/{DEACCESSION_MANIFEST_FILE}"
    try:
        data_object.write(ctx, manifest_path, json.dumps(manifest, indent=4))
    except msi.Error:
        return "Could not generate deaccession manifest."

    # Assign parent ACLs to manifest file
    vault.copy_acls_from_parent(ctx, manifest_path, "default")

    return ""


def revoke_original_access(ctx: rule.Context, coll: str) -> str:
    """Revoke access to data package's original collection.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession

    :returns: Error string, if any
    """
    original_path = f"{coll}/original"

    iter = genquery.row_iterator("ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME",
                                 f"COLL_NAME = '{original_path}'",
                                 genquery.AS_LIST,
                                 ctx)
    for row in iter:
        user_id = row[0]
        user_name = user.name_from_id(ctx, user_id)
        if user_name != "rods":
            try:
                msi.set_acl(ctx, "recursive", "admin:null", user_name, original_path)
            except msi.Error:
                return "Could not revoke access to original collection."

    return ""


def initialize_deaccession(ctx: rule.Context, coll: str) -> None:
    """Initialize deaccession process after approval.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Vault data package in deaccession
    """
    # Generate deaccession manifest file
    manifest_output = generate_deaccession_manifest(ctx, coll)
    if manifest_output != "":
        log.write(ctx, f"initialize_deaccession: {manifest_output}")

    # Revoke access to original data
    access_output = revoke_original_access(ctx, coll)
    if access_output != "":
        log.write(ctx, f"initialize_deaccession: {access_output}")

    # Complete deaccession
    vault_complete_deaccession(ctx, coll)

    # If package is published, landing page and DataCite metadata needs to be updated
    vault_status = vault.get_coll_vault_status(ctx, coll)
    if vault_status == constants.vault_package_state.PUBLISHED:
        # Set PENDING state for publication update
        avu.set_on_coll(ctx, coll, f"{constants.UUORGMETADATAPREFIX}cronjob_publication_update", constants.CRONJOB_STATE['PENDING'])
        publication.set_update_publication_state(ctx, coll)
# }}}


# Deaccession finalization flow {{{
def get_deaccessioned_packages_to_delete(ctx: rule.Context) -> list:
    """Get deaccessioned data packages that still retain original data.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of deaccessioned data packages that still retain original data.
    """
    pending_deletion = []

    deaccessioned = list(genquery.Query(ctx,
                                        "COLL_NAME",
                                        f"META_COLL_ATTR_NAME = '{constants.IIDEACCESSIONSTATUSATTRNAME}' AND META_COLL_ATTR_VALUE = '{constants.vault_deaccession_state.DEACCESSION_COMPLETE.value}'",
                                        output=genquery.AS_LIST))
    for coll in deaccessioned:
        original = list(genquery.Query(ctx,
                                       "COLL_NAME",
                                       f"COLL_NAME like '%original' AND COLL_PARENT_NAME = '{coll[0]}'",
                                       output=genquery.AS_LIST))
        if len(original) > 0:
            pending_deletion.append(coll[0])

    return pending_deletion


def cooldown_passed(ctx: rule.Context, deaccession_date: datetime) -> bool:
    """Check that cooldown period has passed since deaccession date.

    :param ctx:                 Combined type of a callback and rei struct
    :param deaccession_date:    Deaccession date (timestamp)

    :returns: True if cooldown period passed, False otherwise
    """
    cooldown = config.deaccession_cooldown
    cooldown_date = deaccession_date.date() + relativedelta(days=cooldown)
    now = date.today()

    return now > cooldown_date


def deaccession_provenance_present(ctx: rule.Context, coll: str) -> bool:
    """Check provenance log for deaccession logs.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Deaccessioned vault data package

    :returns: True if all deaccession logs are present in the provenance log, False otherwise
    """
    # Retrieve provenance log.
    provenance_logs = list(genquery.Query(ctx,
                                          "ORDER_DESC(META_COLL_ATTR_VALUE)",
                                          f"COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.UUPROVENANCELOG}'",
                                          output=genquery.AS_LIST))

    if not provenance_logs:
        return True

    # Verify that deaccession logs are present in the provenance log.
    required_actions = {"submitted for deaccession", "approved for deaccession", "deaccessioned"}
    found_actions = set()

    # Check if all required deaccession logs are in the provenance log.
    for log_entry in provenance_logs:
        parsed_log = jsonutil.parse(log_entry[0])
        if parsed_log[1] in required_actions:
            found_actions.add(parsed_log[1])

    return found_actions == required_actions


def deaccession_manifest_present(ctx: rule.Context, coll: str) -> bool:
    """Check existence of deaccession manifest file.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Deaccessioned vault data package

    :returns: True if deaccession manifest file is present, False otherwise
    """
    return len(list(genquery.Query(ctx,
                                   "DATA_NAME",
                                   f"DATA_NAME = '{DEACCESSION_MANIFEST_FILE}' AND COLL_NAME = '{coll}'",
                                   output=genquery.AS_LIST))) > 0


def deaccession_delete_original(ctx: rule.Context, coll: str) -> None:
    """Delete original data.

    :param ctx:     Combined type of a callback and rei struct
    :param coll:    Deaccessioned vault data package
    """
    original_path = f"{coll}/original"

    # Give rods ownership of original data
    try:
        msi.set_acl(ctx, "recursive", "admin:own", "rods", original_path)
    except msi.Error:
        log.write(ctx, "deaccession_delete_original: msiError - Could not give rods ownership of original data.")
        return

    # Delete original data
    try:
        collection.remove(ctx, original_path, True)
    except msi.Error:
        log.write(ctx, "deaccession_delete_original: msiError - Could not delete original data.")
        return

    log.write(ctx, f"deaccession_delete_original: Successfully deleted original data of data package {coll}")


@rule.make()
def rule_pending_deaccession_deletion(ctx: rule.Context) -> None:
    """Rule interface for checking for deaccessioned packages that have pending data deletion.

    :param ctx: Combined type of a callback and rei struct
    """
    # Check user here is rods
    if user.name(ctx) != "rods":
        log.write(ctx, "rule_pending_deaccession_deletion: Insufficient permissions - deaccession data deletion can only be performed by rods.")
        return

    # Retrieve deaccessioned packages pending deletion
    pending_deletion = get_deaccessioned_packages_to_delete(ctx)
    if pending_deletion:
        for coll in pending_deletion:
            deaccession_date = get_deaccession_date(ctx, coll)

            # Check that cooldown period has passed
            if cooldown_passed(ctx, deaccession_date):
                log.write(ctx, f"rule_pending_deaccession_deletion: Processing package {coll}...")

                # Confirm that all deaccession logs are present in the provenance log
                if not deaccession_provenance_present(ctx, coll):
                    log.write(ctx, "rule_pending_deaccession_deletion: Cannot delete - Provenance log is missing or shows change after deaccession.")
                    continue

                # Confirm that package is deaccessioned
                deaccession_status = vault_deaccession_status(ctx, coll)
                if constants.vault_deaccession_state(deaccession_status) != constants.vault_deaccession_state.DEACCESSION_COMPLETE:
                    log.write(ctx, "rule_pending_deaccession_deletion: Cannot delete - Package is not deaccessioned.")
                    continue

                # Confirm that package is in valid vault state (UNPUBLISHED, PUBLISHED, DEPUBLISHED)
                vault_status = vault.get_coll_vault_status(ctx, coll)
                if vault_status not in [constants.vault_package_state.UNPUBLISHED, constants.vault_package_state.PUBLISHED, constants.vault_package_state.DEPUBLISHED]:
                    log.write(ctx, "rule_pending_deaccession_deletion: Cannot delete - Package is not in a valid vault state.")
                    continue

                # Confirm that package contains deaccession manifest file
                if not deaccession_manifest_present(ctx, coll):
                    log.write(ctx, "rule_pending_deaccession_deletion: Cannot delete - Package has no deaccession manifest file.")
                    continue

                deaccession_delete_original(ctx, coll)
# }}}
