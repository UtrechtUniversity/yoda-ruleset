# -*- coding: utf-8 -*-
"""Functions to act on user-visible folders in the research or vault area."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import group
import policies_folder_status
import provenance
from util import *
from util.query import Query

__all__ = ['rule_collection_group_name',
           'api_folder_get_locks',
           'api_folder_lock',
           'api_folder_unlock',
           'api_folder_submit',
           'api_folder_unsubmit',
           'api_folder_accept',
           'api_folder_reject']


def set_status(ctx, coll, status):
    """Change a folder's status.

    Status changes are validated by policy (AVU modify preproc).
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

    :param coll: Folder to lock
    """
    return set_status(ctx, coll, constants.research_package_state.LOCKED)


@api.make()
def api_folder_unlock(ctx, coll):
    """Unlock a folder.

    Unlocking is implemented by clearing the folder status. Since this action
    can also represent other state changes than "unlock", we perform a sanity
    check to see if the folder is currently in the expected state.

    :param coll: Folder to unlock
    """
    if get_status(ctx, coll) is not constants.research_package_state.LOCKED:
        return api.Error('status_changed',
                         'Insufficient permissions or the folder is currently not locked')

    return set_status(ctx, coll, constants.research_package_state.FOLDER)


@api.make()
def api_folder_submit(ctx, coll):
    """Submit a folder.

    :param coll: Folder to submit
    """
    return set_status(ctx, coll, constants.research_package_state.SUBMITTED)


@api.make()
def api_folder_unsubmit(ctx, coll):
    """Unsubmit a folder.

    :param coll: Folder to unsubmit
    """
    # Sanity check. See 'unlock'.
    if get_status(ctx, coll) is not constants.research_package_state.SUBMITTED:
        return api.Error('status_changed', 'Folder cannot be unsubmitted because its status has changed.')

    return set_status(ctx, coll, constants.research_package_state.FOLDER)


@api.make()
def api_folder_accept(ctx, coll):
    """Accept a folder.

    :param coll: Folder to accept
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.ACCEPTED)


@api.make()
def api_folder_reject(ctx, coll):
    """Reject a folder.

    :param coll: Folder to reject
    """
    return set_status_as_datamanager(ctx, coll, constants.research_package_state.REJECTED)


@api.make()
def api_folder_secure(ctx, coll):
    """Secure a folder.

    :param coll: Folder to secure
    """
    ctx.iiFolderSecure(coll)


def collection_group_name(callback, coll):
    """Return the name of the group a collection belongs to."""
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

            # Check if group is a research or intake group.
            if group_name.startswith("research-") or group_name.startswith("intake-"):
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
            in Query(ctx, 'META_{}_ATTR_NAME, META_{}_ATTR_VALUE'.format(typ, typ),
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
    return get_locks(ctx, coll)


def has_locks(ctx, coll, org_metadata=None):
    """Check whether a lock exists on the given collection, its parents or children."""
    return len(get_locks(ctx, coll, org_metadata=org_metadata)) > 0


def is_locked(ctx, coll, org_metadata=None):
    """Check whether a lock exists on the given collection itself or a parent collection.

    Locks on subcollections are not counted.
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
        except Exception as e:
            log.write(ctx, 'Invalid folder status <{}>'.format(x))

    return constants.research_package_state.FOLDER


def datamanager_exists(ctx, coll):
    """Check if a datamanager exists for a given collection."""
    group_name = collection_group_name(ctx, coll)
    category = group.get_category(ctx, group_name)

    return group.exists(ctx, "datamanager-" + category)


def post_status_transition(ctx, path, actor, status):
    """Post folder status transition actions."""
    status = constants.research_package_state(status)

    if status is constants.research_package_state.SUBMITTED:
        provenance.log_action(ctx, actor, path, "submitted for vault")

        # Set status to accepted if group has no datamanager.
        if not datamanager_exists(ctx, path):
            set_status(ctx, coll, constants.research_package_state.ACCEPTED)

    elif status is constants.research_package_state.ACCEPTED:
        # Actor is system if group has no datamanager.
        if not datamanager_exists(ctx, path):
            actor = "system"

        provenance.log_action(ctx, actor, path, "accepted for vault")

        # Set state to secure package in vault space.
        attribute = constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault"
        avu.set_on_coll(ctx, path, attribute, constants.CRONJOB_STATE['PENDING'])

    elif status is constants.research_package_state.FOLDER:
        # If previous action was submit and new status is FOLDER action is unsubmit.
        provenance_log = provenance.get_provenance_log(ctx, path)
        if provenance_log[-1][1] == "submitted for vault":
            provenance.log_action(ctx, actor, path, "unsubmitted for vault")
        else:
            provenance.log_action(ctx, actor, path, "unlocked")

    elif status is constants.research_package_state.LOCKED:
        provenance.log_action(ctx, actor, path, "locked")

    elif status is constants.research_package_state.REJECTED:
        provenance.log_action(ctx, actor, path, "rejected for vault")

    elif status is constants.research_package_state.SECURED:
        actor = "system"
        provenance.log_action(ctx, actor, path, "secured in vault")
