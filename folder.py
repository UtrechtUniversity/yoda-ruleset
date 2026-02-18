"""Functions to act on user-visible folders in the research or vault area."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time
import uuid
from typing import List, Tuple

import genquery
import irods_types

import epic
import meta
import notifications
import policies_folder_status
import provenance
import vault
from util import *
from vault_utils import get_sanity_checks_results_copy_to_vault_paths

__all__ = ['rule_collection_group_name',
           'api_folder_get_locks',
           'api_folder_lock',
           'api_folder_unlock',
           'api_folder_submit',
           'api_folder_unsubmit',
           'api_folder_accept',
           'api_folder_reject',
           'rule_folder_secure']


def set_status(ctx: rule.Context, coll: str, status: constants.research_package_state) -> api.Result:
    """Change a folder's status.

    Status changes are validated by policy (AVU modify preproc).

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Folder to change status of
    :param status: Status to change to

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space not in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        return api.Error('invalid_path', 'Invalid folder path.')

    # Ideally we would pass in the current (expected) status as part of the
    # request, and perform a metadata 'mod' operation instead of a 'set'.
    # However no such msi exists.
    # With 'mod' we can be sure that we are performing the correct state
    # transition. Otherwise the original status in a transition can be
    # different from the expected current status, resulting in e.g. a validated
    # SECURED -> FOLDER transition, while the request was for a REJECTED ->
    # FOLDER transition.
    try:
        if status.value == '':
            avu.rmw_from_coll(ctx, coll, constants.IISTATUSATTRNAME, '%')
        else:
            avu.set_on_coll(ctx, coll, constants.IISTATUSATTRNAME, status.value)
    except Exception as e:
        x = policies_folder_status.can_set_folder_status_attr(ctx,
                                                              user.user_and_zone(ctx),
                                                              coll,
                                                              status.value)
        if x:
            return api.Error('internal', 'Could not update folder status due to an internal error', str(e))
        else:
            return api.Error('not_allowed', x.reason)
    return api.Result.ok()


def set_status_as_datamanager(ctx: rule.Context, coll: str, status: constants.research_package_state) -> api.Result:
    """Change a folder's status as a datamanager.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Folder to change status of
    :param status: Status to change to

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space not in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        return api.Error('invalid_path', 'Invalid folder path.')

    res = ctx.iiFolderDatamanagerAction(coll, status.value, '', '')
    if res['arguments'][2] != 'Success':
        return api.Error(*res['arguments'][1:])


@api.make()
def api_folder_lock(ctx: rule.Context, coll: str) -> api.Result:
    """Lock a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to lock

    :returns: API status
    """
    return set_status(ctx, coll, constants.research_package_state.LOCKED)


@api.make()
def api_folder_unlock(ctx: rule.Context, coll: str) -> api.Result:
    """Unlock a folder.

    Unlocking is implemented by clearing the folder status. Since this action
    can also represent other state changes than "unlock", we perform a sanity
    check to see if the folder is currently in the expected state.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to unlock

    :returns: API status
    """
    if get_status(ctx, coll) is not constants.research_package_state.LOCKED:
        return api.Error('status_changed',
                         'Insufficient permissions or the folder is currently not locked')

    return set_status(ctx, coll, constants.research_package_state.FOLDER)


@api.make()
def api_folder_submit(ctx: rule.Context, coll: str, delete_research_copy: bool = False) -> api.Result:
    """Submit a folder.

    :param ctx:                  Combined type of a callback and rei struct
    :param coll:                 Folder to submit
    :param delete_research_copy: Whether to delete copy in research space

    :returns: API status
    """
    if delete_research_copy:
        avu.set_on_coll(ctx, coll, constants.DELETE_RESEARCH_COPY, coll)
    else:
        try:
            research_coll = avu.get_attr_val_of_coll(ctx, coll, constants.DELETE_RESEARCH_COPY)
            avu.rmw_from_coll(ctx, coll, constants.DELETE_RESEARCH_COPY, research_coll)
        except ValueError:
            pass

    return set_status(ctx, coll, constants.research_package_state.SUBMITTED)


@api.make()
def api_folder_unsubmit(ctx: rule.Context, coll: str) -> api.Result:
    """Unsubmit a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to unsubmit

    :returns: API status
    """
    # Sanity check. See 'unlock'.
    if get_status(ctx, coll) is not constants.research_package_state.SUBMITTED:
        return api.Error('status_changed', 'Folder cannot be unsubmitted because its status has changed.')

    return set_status(ctx, coll, constants.research_package_state.FOLDER)


@api.make()
def api_folder_accept(ctx: rule.Context, coll: str) -> api.Result:
    """Accept a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to accept

    :returns: API status
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.ACCEPTED)


@api.make()
def api_folder_reject(ctx: rule.Context, coll: str) -> api.Result:
    """Reject a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to reject

    :returns: API status
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.REJECTED)


@rule.make(inputs=[0], outputs=[1])
def rule_folder_secure(ctx: rule.Context, coll: str) -> str:
    """Rule interface for processing vault status transition request.
    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Collection to be copied to vault

    :return: result of securing action (1 for successfully secured or skipped folder)
    """
    if not precheck_folder_secure(ctx, coll):
        return '1'

    if not folder_secure(ctx, coll):
        folder_secure_set_retry(ctx, coll)
        return '0'

    return '1'


def precheck_folder_secure(ctx: rule.Context, coll: str) -> bool:
    """Whether to continue with securing. Should not touch the retry attempts,
       these are prechecks and don't count toward the retry attempts limit

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to secure

    :returns: True when successful
    """
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "folder_secure: User is not rodsadmin")
        return False

    found, last_run = get_last_run_time(ctx, coll)
    if (not correct_copytovault_start_status(ctx, coll)
            or not correct_copytovault_start_location(coll)
            or not misc.last_run_time_acceptable(found, last_run, config.vault_copy_backoff_time)):
        return False

    return True


def folder_secure(ctx: rule.Context, coll: str) -> bool:
    """Secure a folder to the vault. If the previous copy did not finish, retry

    This function should only be called by a rodsadmin
    and should not be called from the portal.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to secure

    :returns: True when successful
    """

    log.write(ctx, 'folder_secure: Start securing folder <{}>'.format(coll))

    # Checks before start securing
    if not check_folder_secure(ctx, coll):
        return False

    # Set cronjob status
    if not set_cronjob_status(ctx, constants.CRONJOB_STATE['PROCESSING'], coll):
        return False

    # Get the target folder
    target = determine_and_set_vault_target(ctx, coll)
    if not target:
        return False

    # Copy all original info to vault
    if not vault.copy_folder_to_vault(ctx, coll, target):
        return False

    # Starting point of last part of securing a folder into the vault
    # Generate UUID4 and set as Data Package Reference.
    if config.enable_data_package_reference:
        if not avu.set_on_coll(ctx, target, constants.DATA_PACKAGE_REFERENCE, str(uuid.uuid4()), True):
            return False

    meta.copy_user_metadata(ctx, coll, target)
    vault.vault_copy_original_metadata_to_vault(ctx, target)
    vault.vault_write_license(ctx, target)
    group_name = collection_group_name(ctx, coll)

    # Enable indexing on vault target.
    if group_name.startswith("deposit-"):
        vault.vault_enable_indexing(ctx, target)

    # Copy provenance log from research folder to vault package.
    provenance.provenance_copy_log(ctx, coll, target)

    # Try to register EPIC PID if enabled.
    if not set_epic_pid(ctx, target):
        return False

    # Set vault permissions for new vault package.
    if not vault.set_vault_permissions(ctx, coll, target):
        return False

    # Vault package is ready, set vault package state to UNPUBLISHED.
    if not avu.set_on_coll(ctx, target, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.UNPUBLISHED.value, True):
        if vault.get_coll_vault_status(ctx, target) != constants.vault_package_state.UNPUBLISHED:
            return False

    if not set_acl_check(ctx, "recursive", "admin:write", coll, 'Could not set ACL (admin:write) for collection: ' + coll):
        return False
    set_acl_parents(ctx, "recursive", "admin:write", coll)

    # Save vault package for notification.
    set_vault_data_package(ctx, coll, target)

    # Everything is done, set research folder state to SECURED.
    if not folder_secure_succeed_avus(ctx, coll, group_name):
        return False

    # Check if the collection still exists, before changing the ACLs.
    # Research/deposit collections may be deleted after moving to vault.
    if collection.exists(ctx, coll):
        set_acl_check(ctx, "recursive", "admin:null", coll, "Could not set ACL (admin:null) for collection: {}".format(coll))
        set_acl_parents(ctx, "default", "admin:null", coll)

    # All (mostly) went well
    return True


def check_folder_secure(ctx: rule.Context, coll: str) -> bool:
    """Some initial set up that determines whether folder secure can continue.
       These WILL affect the retry attempts.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to secure

    :returns: True when successful
    """
    if (not set_can_modify(ctx, coll)
            or not retry_attempts(ctx, coll)
            or not set_last_run_time(ctx, coll)):
        return False

    return True


def correct_copytovault_start_status(ctx: rule.Context, coll: str) -> bool:
    """Confirm that the copytovault cronjob avu status is correct state to start securing"""
    cronjob_status = get_cronjob_status(ctx, coll)
    if cronjob_status in (constants.CRONJOB_STATE['PENDING'], constants.CRONJOB_STATE['RETRY']):
        return True

    return False


def correct_copytovault_start_location(coll: str) -> bool:
    """Confirm that the folder to be copied is in the correct location.
       For example: in a research or deposit folder and not in the trash.

    :param coll:   Source collection (folder being secured)

    :returns: True when a valid start location
    """
    space, _, _, _ = pathutil.info(coll)
    return space in (pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT)


def get_last_run_time(ctx: rule.Context, coll: str) -> Tuple[bool, int]:
    """Get the last run time, if found"""
    found = False
    last_run = 1
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = '" + constants.IICOPYLASTRUN + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        last_run = int(row[0])
        found = True

    return found, last_run


def set_last_run_time(ctx: rule.Context, coll: str) -> bool:
    """Set last run time, return True for successful set"""
    now = int(time.time())
    return avu.set_on_coll(ctx, coll, constants.IICOPYLASTRUN, str(now), True)


def set_can_modify(ctx: rule.Context, coll: str) -> bool:
    """Check if have permission to modify, set if necessary"""
    check_access_result = msi.check_access(ctx, coll, 'read_object', irods_types.BytesBuf())
    read_access = check_access_result['arguments'][2]
    if read_access != b'\x01':
        # This allows us permission to copy the files
        if not set_acl_check(ctx, "recursive", "admin:read", coll, "Could not set ACL (admin:read) for collection: {}".format(coll)):
            return False

    check_access_result = msi.check_access(ctx, coll, 'modify_object', irods_types.BytesBuf())
    modify_access = check_access_result['arguments'][2]
    if modify_access != b'\x01':
        # This allows us permission to set AVUs
        if not set_acl_check(ctx, "default", "admin:write", coll, "Could not set ACL (admin:write) for collection: {}".format(coll)):
            return False

    return True


def get_retry_count(ctx: rule.Context, coll: str) -> int:
    """ Get the retry count, if not such AVU, return 0 """
    retry_count = 0
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE, COLL_NAME",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = '" + constants.IICOPYRETRYCOUNT + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        retry_count = int(row[0])

    return retry_count


def retry_attempts(ctx: rule.Context, coll: str) -> bool:
    """ Check if there have been too many retries. """
    retry_count = get_retry_count(ctx, coll)

    if retry_count >= config.vault_copy_max_retries:
        return False

    return True


def folder_secure_succeed_avus(ctx: rule.Context, coll: str, group_name: str) -> bool:
    """Set/rm AVUs on source folder when successfully secured folder"""
    org_metadata = dict(get_org_metadata(ctx, coll))

    # In cases where copytovault only ran once, okay that these attributes were not created
    if constants.IICOPYRETRYCOUNT in org_metadata:
        if not avu.rmw_from_coll(ctx, coll, constants.IICOPYRETRYCOUNT, '%', catch=True):
            return False
    if constants.IICOPYLASTRUN in org_metadata:
        if not avu.rmw_from_coll(ctx, coll, constants.IICOPYLASTRUN, '%', catch=True):
            return False

    # Set cronjob status to final state before deletion
    if not set_cronjob_status(ctx, constants.CRONJOB_STATE['OK'], coll):
        return False

    if not rm_cronjob_status(ctx, coll):
        return False

    # Note: this is the status that must always be one of the last to be set
    # on folder, otherwise could be a problem for deposit groups
    if constants.IISTATUSATTRNAME in org_metadata:
        if not avu.rmw_from_coll(ctx, coll, constants.IISTATUSATTRNAME, '%', catch=True):
            return False

    # Remove target AVU on source folder. This should be done after all possibly failing steps
    # have occurred in folder_secure (any "return False" steps), so that if those trip a retry state,
    # on retry folder_secure can reuse the target from before.
    if collection.exists(ctx, coll) and constants.IICOPYPARAMSNAME in org_metadata:
        if not avu.rmw_from_coll(ctx, coll, constants.IICOPYPARAMSNAME, "%", catch=True):
            return False

    return True


def folder_secure_set_retry(ctx: rule.Context, coll: str) -> None:
    # When a folder secure fails, try to set the retry AVU and other applicable AVUs on source folder.
    # If too many attempts, fail.
    new_retry_count = get_retry_count(ctx, coll) + 1
    if new_retry_count > config.vault_copy_max_retries:
        folder_secure_fail(ctx, coll)
        send_folder_secure_notification(ctx, coll, "Data package failed to copy to vault after maximum retries")
    elif not folder_secure_set_retry_avus(ctx, coll, new_retry_count):
        send_folder_secure_notification(ctx, coll, "Failed to set retry state on data package")


def folder_secure_set_retry_avus(ctx: rule.Context, coll: str, retry_count: int) -> bool:
    avu.set_on_coll(ctx, coll, constants.IICOPYRETRYCOUNT, str(retry_count), True)
    return set_cronjob_status(ctx, constants.CRONJOB_STATE['RETRY'], coll)


def folder_secure_fail(ctx: rule.Context, coll: str) -> None:
    """When there are too many retries, give up, set the AVUs and send notifications"""
    # Errors are caught here in hopes that will still be able to set UNRECOVERABLE status at least
    avu.rmw_from_coll(ctx, coll, constants.IICOPYRETRYCOUNT, "%", catch=True)
    # Remove target AVU
    avu.rmw_from_coll(ctx, coll, constants.IICOPYPARAMSNAME, "%", catch=True)
    set_cronjob_status(ctx, constants.CRONJOB_STATE['UNRECOVERABLE'], coll)


def send_folder_secure_notification(ctx: rule.Context, coll: str, message: str) -> None:
    """Send notification about folder secure to relevant datamanagers"""
    if datamanager_exists(ctx, coll):
        try:
            datamanagers = get_datamanagers(ctx, coll)
        except ValueError as e:
            log.write(ctx, f"Unable to send folder secure notifications for <{coll}>: cannot get data managers: {str(e)}")
            datamanagers = []

        for datamanager in datamanagers:
            datamanager_name = '{}#{}'.format(*datamanager)
            notifications.set(ctx, "system", datamanager_name, coll, message)


def set_epic_pid(ctx: rule.Context, target: str) -> bool:
    """Try to set epic pid, if fails return False"""
    if config.epic_pid_enabled:
        ret = epic.register_epic_pid(ctx, target)
        url = ret['url']
        pid = ret['pid']
        http_code = ret['httpCode']

        if http_code not in ('0', '200', '201'):
            # Something went wrong while registering EPIC PID, return false so retry status will be set
            log.write(ctx, "folder_secure: epic pid returned http <{}>".format(http_code))
            return False

        if http_code != "0":
            # save EPIC Persistent ID in metadata
            epic.save_epic_pid(ctx, target, url, pid)

    return True


def get_cronjob_status(ctx: rule.Context, coll: str) -> str | None:
    """Get the cronjob status of given collection"""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        return row[0]

    return None


def rm_cronjob_status(ctx: rule.Context, coll: str) -> bool:
    """Remove cronjob_copy_to_vault attribute on source collection

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Source collection (folder that was being secured)

    :returns: True when successfully removed
    """
    return avu.rmw_from_coll(ctx, coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault", "%", catch=True)


def set_cronjob_status(ctx: rule.Context, status: str, coll: str) -> bool:
    """Set cronjob_copy_to_vault attribute on source collection

    :param ctx:    Combined type of a callback and rei struct
    :param status: Status to set on collection
    :param coll:   Source collection (folder being secured)

    :returns: True when successfully set
    """
    return avu.set_on_coll(ctx, coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault", status, catch=True)


def set_acl_parents(ctx: rule.Context, acl_recurse: str, acl_type: str, coll: str) -> None:
    """Set ACL for parent collections"""
    parent, _ = pathutil.chop(coll)
    while parent != "/" + user.zone(ctx) + "/home":
        set_acl_check(ctx, acl_recurse, acl_type, parent, "Could not set the ACL ({}) on {}".format(acl_type, parent))
        parent, _ = pathutil.chop(parent)


def set_acl_check(ctx: rule.Context, acl_recurse: str, acl_type: str, coll: str, error_msg: str = '') -> bool:
    """Set the ACL if possible, log error_msg if it goes wrong"""
    # TODO turn acl_recurse into a boolean
    try:
        msi.set_acl(ctx, acl_recurse, acl_type, user.full_name(ctx), coll)
    except msi.Error:
        if error_msg:
            log.write(ctx, error_msg)
        return False

    return True


def get_existing_vault_target(ctx: rule.Context, coll: str) -> Tuple[bool, str]:
    """Determine vault target on coll, if it was already determined before """
    found = False
    target = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = '" + constants.IICOPYPARAMSNAME + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        target = row[0]
        found = True

    return found, target


def set_vault_target(ctx: rule.Context, coll: str, target: str) -> bool:
    """Create vault target and AVUs"""
    msi.coll_create(ctx, target, '', irods_types.BytesBuf())
    if not avu.set_on_coll(ctx, target, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.INCOMPLETE.value, True):
        return False

    # Note on the source the target folder in case a copy stops midway
    if not avu.set_on_coll(ctx, coll, constants.IICOPYPARAMSNAME, target, True):
        return False

    return True


def determine_and_set_vault_target(ctx: rule.Context, coll: str) -> str:
    """Determine and set target on coll"""
    found, target = get_existing_vault_target(ctx, coll)

    # Overwrite vault target if it does not pass sanity checks. This should usually
    # fix any wrong vault target. There's a second check in the copy_folder_to_vault
    # function to prevent TOCTOU issues.
    sanity_check_results = get_sanity_checks_results_copy_to_vault_paths(coll, target)
    if len(sanity_check_results) > 0:
        log.write(ctx, "folder_secure: overwriting previous vault target for " + coll
                       + "(" + target + "), because it did not meet sanity checks: "
                       + str(sanity_check_results))
        found = False

    # Determine vault target if it does not exist.
    if not found:
        target = determine_new_vault_target(ctx, coll)
        if target == "":
            log.write(ctx, "folder_secure: No possible vault target found")
            return ""

        # Create vault target and set status to INCOMPLETE.
        if not set_vault_target(ctx, coll, target):
            return ""

    return target


def determine_new_vault_target(ctx: rule.Context, folder: str) -> str:
    """Determine vault target path for a folder."""

    group = collection_group_name(ctx, folder)
    if group == '':
        log.write(ctx, "Cannot determine which deposit or research group <{}> belongs to".format(folder))
        return ""

    parts = group.split('-')
    base_name = '-'.join(parts[1:])

    parts = folder.split('/')
    datapackage_name = parts[-1]

    if len(datapackage_name) > 235:
        datapackage_name = datapackage_name[0:235]

    ret = msi.get_icat_time(ctx, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    vault_group_name = constants.IIVAULTPREFIX + base_name

    # Ensure vault target does not exist.
    i = 0
    target_base = "/" + user.zone(ctx) + "/home/" + vault_group_name + "/" + datapackage_name + "[" + timestamp + "]"
    target = target_base
    while collection.exists(ctx, target):
        i += 1
        target = target_base + "[" + str(i) + "]"

    return target


def collection_group_name(ctx: rule.Context, coll: str) -> str:
    """Return the name of the group a collection belongs to."""

    if pathutil.info(coll).space is pathutil.Space.DEPOSIT:
        coll, _ = pathutil.chop(coll)

    # Retrieve all access user IDs on collection.
    iter = genquery.row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '{}'".format(coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        id = row[0]

        # Retrieve all group names with this ID.
        iter2 = genquery.row_iterator(
            "USER_GROUP_NAME",
            "USER_GROUP_ID = '{}'".format(id),
            genquery.AS_LIST, ctx
        )

        for row2 in iter2:
            group_name = row2[0]

            # Check if group is a research, deposit or intake group.
            if group_name.startswith("research-") or group_name.startswith("deposit-") or group_name.startswith("intake-"):
                return group_name

    for row in iter:
        id = row[0]
        for row2 in iter2:
            group_name = row2[0]

            # Check if group is a datamanager or vault group.
            if group_name.startswith("datamanager-") or group_name.startswith("vault-"):
                return group_name

    # No results found. Not a group folder
    log.write(ctx, "{} does not belong to a research or intake group or is not available to current user.".format(coll))
    return ""


rule_collection_group_name = rule.make(inputs=[0], outputs=[1])(collection_group_name)


def get_org_metadata(ctx: rule.Context, path: str, object_type: pathutil.ObjectType = pathutil.ObjectType.COLL) -> List[Tuple[str, str]]:
    """Obtain a (k,v) list of all organisation metadata on a given collection or data object."""
    prefix = constants.UUORGMETADATAPREFIX
    if object_type is pathutil.ObjectType.DATA:
        coll_name, data_name = pathutil.chop(path)
        coll_name = misc.escape(coll_name)
        return list(genquery.Query(ctx, 'META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE',
                                   f"META_DATA_ATTR_NAME like '{prefix}%' AND COLL_NAME = '{coll_name}' AND DATA_NAME = '{data_name}'"))
    else:
        path = misc.escape(path)
        return list(genquery.Query(ctx, "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                   f"META_COLL_ATTR_NAME like '{prefix}%' AND COLL_NAME = '{path}'"))


def get_locks(ctx: rule.Context, path: str, org_metadata: List[Tuple[str, str]] | None = None, object_type: pathutil.ObjectType = pathutil.ObjectType.COLL) -> List[str]:
    """Return all locks on a collection or data object (includes locks on parents and children)."""
    if org_metadata is None:
        org_metadata = get_org_metadata(ctx, path, object_type=object_type)

    return [root for k, root in org_metadata
            if k == constants.IILOCKATTRNAME
            and (root.startswith(path) or path.startswith(root))]


@api.make()
def api_folder_get_locks(ctx: rule.Context, coll: str) -> api.Result:
    """Return a list of locks on a collection."""
    locks = []

    for lock in get_locks(ctx, coll):
        _, _, path, subpath = pathutil.info(lock)
        if subpath != '':
            path = path + "/" + subpath
        locks.append("/{}".format(path))

    return locks


def has_locks(ctx: rule.Context, coll: str, org_metadata: List[Tuple[str, str]] | None = None) -> bool:
    """Check whether a lock exists on the given collection, its parents or children."""
    return len(get_locks(ctx, coll, org_metadata=org_metadata)) > 0


def is_locked(ctx: rule.Context, coll: str, org_metadata: List[Tuple[str, str]] | None = None) -> bool:
    """Check whether a lock exists on the given collection itself or a parent collection.

    Locks on subcollections are not counted.

    :param ctx:          Combined type of a callback and rei struct
    :param coll:         Collection to check for locks
    :param org_metadata: Organizational metadata

    :returns: Boolean indicating if folder is locked
    """
    locks = get_locks(ctx, coll, org_metadata=org_metadata)

    # Count only locks that exist on the coll itself or its parents.
    return len([x for x in locks if coll.startswith(x)]) > 0


def is_data_locked(ctx: rule.Context, path: str, org_metadata: List[Tuple[str, str]] | None = None) -> bool:
    """Check whether a lock exists on the given data object."""
    locks = get_locks(ctx, path, org_metadata=org_metadata, object_type=pathutil.ObjectType.DATA)

    return len(locks) > 0


def get_status(ctx: rule.Context, path: str, org_metadata: List[Tuple[str, str]] | None = None) -> constants.research_package_state:
    """Get the status of a research folder."""
    if org_metadata is None:
        org_metadata = get_org_metadata(ctx, path)

    # Don't care about duplicate attr names here.
    org_metadata_dict = dict(org_metadata)
    if constants.IISTATUSATTRNAME in org_metadata_dict:
        x = org_metadata_dict[constants.IISTATUSATTRNAME]
        try:
            x = "" if x == "FOLDER" else x
            return constants.research_package_state(x)
        except Exception:
            log.write(ctx, 'Invalid folder status <{}>'.format(x))

    return constants.research_package_state.FOLDER


def datamanager_exists(ctx: rule.Context, coll: str) -> bool:
    """Check if a datamanager exists for a given collection.

    :param ctx:          Combined type of a callback and rei struct
    :param coll:         Collection of group (e.g. /tempZone/home/research-foo)

    :raises ValueError: If collection does not match a group or the group
                        is invalid.
    :returns: Boolean indicating if datamanager group exists for group of collection

       """
    group_name = collection_group_name(ctx, coll)
    if group_name == "":
        raise ValueError(f"Error: cannot determine group of collection {coll}.")
    category = group.get_category(ctx, group_name)
    if category is None:
        # Group without category is invalid.
        raise ValueError(f"Error: group for collection {coll} is invalid. It has no category.")
    return group.exists(ctx, "datamanager-" + category)


def get_datamanagers(ctx: rule.Context, coll: str) -> List[Tuple[str, str]]:
    """Retrieve datamanagers for a given collection.

    :param ctx:          Combined type of a callback and rei struct
    :param coll:         Collection of group (e.g. /tempZone/home/research-foo)

    :raises ValueError: If collection does not match a group or refers to an
                        invalid group.
    :returns: List of data manager users for research collection. Each
              user item in the list is a tuple of username and zone.
    """
    group_name = collection_group_name(ctx, coll)
    if group_name == "":
        raise ValueError(f"Error: cannot determine group of collection {coll}.")
    category = group.get_category(ctx, group_name)

    if category is None:
        # Group without category is invalid.
        raise ValueError(f"Error: group for collection {coll} is invalid. It has no category.")
    else:
        return group.members(ctx, "datamanager-" + category)


def set_submitter(ctx: rule.Context, path: str, actor: str) -> None:
    """Set submitter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "submitted_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_submitter(ctx: rule.Context, path: str) -> str:
    """Get submitter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "submitted_actor"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_accepter(ctx: rule.Context, path: str, actor: str) -> None:
    """Set accepter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "accepted_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_accepter(ctx: rule.Context, path: str) -> str:
    """Get accepter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "accepted_actor"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_vault_data_package(ctx: rule.Context, path: str, vault: str) -> None:
    """Set vault data package for deposit."""
    attribute = constants.UUORGMETADATAPREFIX + "vault_data_package"
    avu.set_on_coll(ctx, path, attribute, vault)


def get_vault_data_package(ctx: rule.Context, path: str) -> str:
    """Get vault data package for deposit."""
    attribute = constants.UUORGMETADATAPREFIX + "vault_data_package"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""
