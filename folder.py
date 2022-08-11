# -*- coding: utf-8 -*-
"""Functions to act on user-visible folders in the research or vault area."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import uuid

import genquery
import irods_types

import epic
import groups
import meta
import policies_folder_status
import provenance
import vault
from util import *

__all__ = ['rule_collection_group_name',
           'api_folder_get_locks',
           'api_folder_lock',
           'api_folder_unlock',
           'api_folder_submit',
           'api_folder_unsubmit',
           'api_folder_accept',
           'api_folder_reject',
           'rule_folder_secure']


def set_status(ctx, coll, status):
    """Change a folder's status.

    Status changes are validated by policy (AVU modify preproc).

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Folder to change status of
    :param status: Status to change to

    :returns: API status
    """
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


def set_status_as_datamanager(ctx, coll, status):
    """Change a folder's status as a datamanager."""
    res = ctx.iiFolderDatamanagerAction(coll, status.value, '', '')
    if res['arguments'][2] != 'Success':
        return api.Error(*res['arguments'][1:])


@api.make()
def api_folder_lock(ctx, coll):
    """Lock a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to lock

    :returns: API status
    """
    return set_status(ctx, coll, constants.research_package_state.LOCKED)


@api.make()
def api_folder_unlock(ctx, coll):
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
def api_folder_submit(ctx, coll):
    """Submit a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to submit

    :returns: API status
    """
    return set_status(ctx, coll, constants.research_package_state.SUBMITTED)


@api.make()
def api_folder_unsubmit(ctx, coll):
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
def api_folder_accept(ctx, coll):
    """Accept a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to accept

    :returns: API status
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.ACCEPTED)


@api.make()
def api_folder_reject(ctx, coll):
    """Reject a folder.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to reject

    :returns: API status
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.REJECTED)


@rule.make(inputs=[0, 1], outputs=[2])
def rule_folder_secure(ctx, coll, target):

    """Rule interface for processing vault status transition request.
    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Collection to be copied to vault
    :param target:          Vault target to copy research package to including license file etc

    :return: returns result of securing action
    """
    return folder_secure(ctx, coll, target)


def folder_secure(ctx, coll, target):
    """Secure a folder to the vault.

    This function should only be called by a rodsadmin
    and should not be called from the portal.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Folder to secure
    :param target: Target folder in vault

    :returns: '0' when nu error occurred
    """
    """
    # Following code is overturned by code in the rule language.
    # This, as large files were not properly copied to the vault.
    # Using the rule language this turned out to work fine.

    log.write(ctx, 'folder_secure: Start securing folder <{}>'.format(coll))

    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "folder_secure: User is no rodsadmin")
        return '1'

    # Check modify access on research folder.
    msi.check_access(ctx, coll, 'modify object', irods_types.BytesBuf())

    modify_access = msi.check_access(ctx, coll, 'modify object', irods_types.BytesBuf())['arguments'][2]

    # Set cronjob status
    if modify_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:write", user.full_name(ctx), coll)
        except msi.Error as e:
            log.write(ctx, "Could not set acl (admin:write) for collection: " + coll)
            return '1'

    avu.set_on_coll(ctx, coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault", constants.CRONJOB_STATE['PROCESSING'])

    found = False
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = '" + constants.IICOPYPARAMSNAME + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        target = row[0]
        found = True

    if found:
        avu.rm_from_coll(ctx, coll, constants.IICOPYPARAMSNAME, target)

    if modify_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), coll)
        except msi.Error as e:
            log.write(ctx, "Could not set acl (admin:null) for collection: " + coll)
            return '1'

    # Determine vault target if it does not exist.
    if not found:
        target = determine_vault_target(ctx, coll)
        if target == "":
            log.write(ctx, "folder_secure: No vault target found")
            return '1'

        # Create vault target and set status to INCOMPLETE.
        msi.coll_create(ctx, target, '', irods_types.BytesBuf())
        avu.set_on_coll(ctx, target, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.INCOMPLETE)

    # Copy all original info to vault
    # try:
    # vault.copy_folder_to_vault(ctx, coll, target)
    # except Exception as e:
    # log.write(ctx, e)
    # return '1'

    ctx.iiCopyFolderToVault(coll, target)
    """
    # Starting point of last part of securing a folder into the vault
    msi.check_access(ctx, coll, 'modify object', irods_types.BytesBuf())
    modify_access = msi.check_access(ctx, coll, 'modify object', irods_types.BytesBuf())['arguments'][2]

    # Generate UUID4 and set as Data Package Reference.
    if config.enable_data_package_reference:
        avu.set_on_coll(ctx, target, constants.DATA_PACKAGE_REFERENCE, str(uuid.uuid4()))

    meta.copy_user_metadata(ctx, coll, target)
    vault.vault_copy_original_metadata_to_vault(ctx, target)
    vault.vault_write_license(ctx, target)

    # Copy provenance log from research folder to vault package.
    provenance.provenance_copy_log(ctx, coll, target)

    # Try to register EPIC PID if enabled.
    if config.epic_pid_enabled:
        ret = epic.register_epic_pid(ctx, target)
        url = ret['url']
        pid = ret['pid']
        http_code = ret['httpCode']

        if (http_code != "0" and http_code != "200" and http_code != "201"):
            # Something went wrong while registering EPIC PID, set cronjob state to retry.
            log.write(ctx, "folder_secure: epid pid returned http <{}>".format(http_code))
            if modify_access != b'\x01':
                try:
                    msi.set_acl(ctx, "default", "admin:write", user.full_name(ctx), coll)
                except msi.Error:
                    return '1'

            avu.set_on_coll(ctx, coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault", constants.CRONJOB_STATE['RETRY'])
            avu.set_on_coll(ctx, coll, constants.IICOPYPARAMSNAME, target)

            if modify_access != b'\x01':
                try:
                    msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), coll)
                except msi.Error:
                    log.write(ctx, "Could not set acl (admin:null) for collection: " + coll)
                    return '1'

        if http_code != "0":
            # save EPIC Persistent ID in metadata
            epic.save_epic_pid(ctx, target, url, pid)

    # Set vault permissions for new vault package.
    group = collection_group_name(ctx, coll)
    if group == '':
        log.write(ctx, "folder_secure: Cannot determine which deposit or research group <{}> belongs to".format(coll))
        return '1'

    vault.set_vault_permissions(ctx, group, coll, target)

    # Set cronjob status to OK.
    if modify_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:write", user.full_name(ctx), coll)
        except msi.Error:
            log.write(ctx, "Could not set acl (admin:write) for collection: " + coll)
            return '1'

    avu.set_on_coll(ctx, coll, constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault", constants.CRONJOB_STATE['OK'])

    if modify_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), coll)
        except msi.Error:
            log.write(ctx, "Could not set acl (admin:null) for collection: " + coll)
            return '1'

    # Vault package is ready, set vault package state to UNPUBLISHED.
    avu.set_on_coll(ctx, target, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.UNPUBLISHED)

    # Everything is done, set research folder state to SECURED.
    try:
        msi.set_acl(ctx, "recursive", "admin:write", user.full_name(ctx), coll)
    except msi.Error:
        log.write(ctx, "Could not set acl (admin:write) for collection: " + coll)
        return '1'

    parent, chopped_coll = pathutil.chop(coll)
    while parent != "/" + user.zone(ctx) + "/home":
        try:
            msi.set_acl(ctx, "default", "admin:write", user.full_name(ctx), parent)
        except msi.Error:
            log.write(ctx, "Could not set ACL on " + parent)
        parent, chopped_coll = pathutil.chop(parent)

    # Save vault package for notification.
    set_vault_data_package(ctx, coll, target)

    # Set folder status to SECURED.
    avu.set_on_coll(ctx, coll, constants.IISTATUSATTRNAME, constants.research_package_state.SECURED)

    try:
        msi.set_acl(ctx, "recursive", "admin:null", user.full_name(ctx), coll)
    except msi.Error:
        log.write(ctx, "Could not set acl (admin:null) for collection: " + coll)

    parent, chopped_coll = pathutil.chop(coll)
    while parent != "/" + user.zone(ctx) + "/home":
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), parent)
        except msi.Error:
            log.write(ctx, "Could not set ACL (admin:null) on " + parent)

        parent, chopped_coll = pathutil.chop(parent)

    # All went well
    return '0'


def determine_vault_target(ctx, folder):
    """Determine vault target path for a folder."""

    group = collection_group_name(ctx, folder)
    if group == '':
        log.write(ctx, "Cannot determine which deposit or research group " + + " belongs to")
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


def collection_group_name(callback, coll):
    """Return the name of the group a collection belongs to."""

    if pathutil.info(coll).space is pathutil.Space.DEPOSIT:
        coll, _ = pathutil.chop(coll)

    # Retrieve all access user IDs on collection.
    iter = genquery.row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '{}'".format(coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        id = row[0]

        # Retrieve all group names with this ID.
        iter2 = genquery.row_iterator(
            "USER_GROUP_NAME",
            "USER_GROUP_ID = '{}'".format(id),
            genquery.AS_LIST, callback
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
    log.write(callback, "{} does not belong to a research or intake group or is not available to current user.".format(coll))
    return ""


rule_collection_group_name = rule.make(inputs=[0], outputs=[1])(collection_group_name)


def get_org_metadata(ctx, path, object_type=pathutil.ObjectType.COLL):
    """Obtain a (k,v) list of all organisation metadata on a given collection or data object."""
    typ = 'DATA' if object_type is pathutil.ObjectType.DATA else 'COLL'

    return [(k, v) for k, v
            in genquery.Query(ctx, 'META_{}_ATTR_NAME, META_{}_ATTR_VALUE'.format(typ, typ),
                              "META_{}_ATTR_NAME like '{}%'".format(typ, constants.UUORGMETADATAPREFIX)
                              + (" AND COLL_NAME = '{}' AND DATA_NAME = '{}'".format(*pathutil.chop(path))
                                 if object_type is pathutil.ObjectType.DATA
                                 else " AND COLL_NAME = '{}'".format(path)))]


def get_locks(ctx, path, org_metadata=None, object_type=pathutil.ObjectType.COLL):
    """Return all locks on a collection or data object (includes locks on parents and children)."""
    if org_metadata is None:
        org_metadata = get_org_metadata(ctx, path, object_type=object_type)

    return [root for k, root in org_metadata
            if k == constants.IILOCKATTRNAME
            and (root.startswith(path) or path.startswith(root))]


@api.make()
def api_folder_get_locks(ctx, coll):
    """Return a list of locks on a collection."""
    locks = []

    for lock in get_locks(ctx, coll):
        _, _, path, subpath = pathutil.info(lock)
        if subpath != '':
            path = path + "/" + subpath
        locks.append("/{}".format(path))

    return locks


def has_locks(ctx, coll, org_metadata=None):
    """Check whether a lock exists on the given collection, its parents or children."""
    return len(get_locks(ctx, coll, org_metadata=org_metadata)) > 0


def is_locked(ctx, coll, org_metadata=None):
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


def is_data_locked(ctx, path, org_metadata=None):
    """Check whether a lock exists on the given data object."""
    locks = get_locks(ctx, path, org_metadata=org_metadata, object_type=pathutil.ObjectType.DATA)

    return len(locks) > 0


def get_status(ctx, path, org_metadata=None):
    """Get the status of a research folder."""
    if org_metadata is None:
        org_metadata = get_org_metadata(ctx, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if constants.IISTATUSATTRNAME in org_metadata:
        x = org_metadata[constants.IISTATUSATTRNAME]
        try:
            return constants.research_package_state(x)
        except Exception:
            log.write(ctx, 'Invalid folder status <{}>'.format(x))

    return constants.research_package_state.FOLDER


def datamanager_exists(ctx, coll):
    """Check if a datamanager exists for a given collection."""
    group_name = collection_group_name(ctx, coll)
    category = group.get_category(ctx, group_name)

    return group.exists(ctx, "datamanager-" + category)


def get_datamanagers(ctx, coll):
    """Retrieve datamanagers for a given collection."""
    group_name = collection_group_name(ctx, coll)
    category = group.get_category(ctx, group_name)

    return group.members(ctx, "datamanager-" + category)


def set_submitter(ctx, path, actor):
    """Set submitter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "submitted_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_submitter(ctx, path):
    """Get submitter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "submitted_actor"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return None


def set_accepter(ctx, path, actor):
    """Set accepter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "accepted_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_accepter(ctx, path):
    """Get accepter of folder for the vault."""
    attribute = constants.UUORGMETADATAPREFIX + "accepted_actor"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return None


def set_vault_data_package(ctx, path, vault):
    """Set vault data package for deposit."""
    attribute = constants.UUORGMETADATAPREFIX + "vault_data_package"
    avu.set_on_coll(ctx, path, attribute, vault)


def get_vault_data_package(ctx, path):
    """Get vault data package for deposit."""
    attribute = constants.UUORGMETADATAPREFIX + "vault_data_package"
    org_metadata = dict(get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return None
