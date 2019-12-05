# -*- coding: utf-8 -*-
"""Functions to retrieve unformation about collections."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

from util import *

__all__ = ['rule_uu_collection_group_name',
           'api_uu_collection_lock',
           'api_uu_collection_unlock',
           'api_uu_collection_submit',
           'api_uu_collection_unsubmit',
           'api_uu_collection_accept',
           'api_uu_collection_reject']


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


api_uu_collection_lock     = api.make()(lock)
api_uu_collection_unlock   = api.make()(unlock)
api_uu_collection_submit   = api.make()(submit)
api_uu_collection_unsubmit = api.make()(unsubmit)
api_uu_collection_accept   = api.make()(accept)
api_uu_collection_reject   = api.make()(reject)


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
