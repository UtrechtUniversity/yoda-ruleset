# -*- coding: utf-8 -*-
"""Functions to act on user-visible folders in the research or vault area."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


from util import *

__all__ = ['rule_uu_collection_group_name',
           'api_uu_folder_lock',
           'api_uu_folder_unlock',
           'api_uu_folder_submit',
           'api_uu_folder_unsubmit',
           'api_uu_folder_accept',
           'api_uu_folder_reject']

def lock(ctx, coll):
    res = ctx.iiFolderLock(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])

def unlock(ctx, coll):
    res = ctx.iiFolderUnlock(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])

def submit(ctx, coll):
    res = ctx.iiFolderSubmit(coll, '', '', '')
    if res['arguments'][2] != 'Success':
        return api.Error(*res['arguments'][2:])
    return res['arguments'][1]

def unsubmit(ctx, coll):
    res = ctx.iiFolderUnsubmit(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])

def accept(ctx, coll):
    res = ctx.iiFolderAccept(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])

def reject(ctx, coll):
    res = ctx.iiFolderReject(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])


api_uu_folder_lock     = api.make()(lock)
api_uu_folder_unlock   = api.make()(unlock)
api_uu_folder_submit   = api.make()(submit)
api_uu_folder_unsubmit = api.make()(unsubmit)
api_uu_folder_accept   = api.make()(accept)
api_uu_folder_reject   = api.make()(reject)

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


rule_uu_collection_group_name = rule.make(inputs=[0], outputs=[1])(collection_group_name)

def get_org_metadata(ctx, coll):
    """Obtains a (k,v) list of all organisation metadata on a given collection"""

    return [(k, v) for k, v
            in genquery.row_iterator("META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME like '{}%'"
                                     .format(coll, constants.UUORGMETADATAPREFIX),
                                     genquery.AS_LIST, ctx)]


def get_locks(ctx, coll, org_metadata=None):
    """Returns all locks on a collection."""

    if org_metadata is None:
        org_metadata = get_org_metadata(ctx, coll)

    return [root for k, root in org_metadata
            if  k == constants.IILOCKATTRNAME
            and (root.startswith(coll) or coll.startswith(root))]

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
