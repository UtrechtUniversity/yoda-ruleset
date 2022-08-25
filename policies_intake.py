# -*- coding: utf-8 -*-
"""iRODS policy implementations."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

import intake_scan
from util import *


def is_data_in_locked_dataset(ctx, actor, path):
    """ Check whether given data object is within a locked dataset """
    dataset_id = ''
    coll = pathutil.chop(path)[0]
    data_name = pathutil.chop(path)[1]

    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "DATA_NAME = '" + data_name + "' AND META_DATA_ATTR_NAME = 'dataset_id' AND COLL_NAME = '" + coll + "' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dataset_id = row[0]
        log.debug(ctx, 'dataset found: ' + dataset_id)

        # now check whether a lock exists
        # Find the toplevel and get the collection check whether is locked
        iter = genquery.row_iterator(
            "COLL_NAME",
            "META_COLL_ATTR_VALUE = '" + dataset_id + "' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
            genquery.AS_LIST, ctx
        )
        toplevel_collection = ''
        toplevel_is_collection = False
        for row in iter:
            toplevel_collection = row[0]
            toplevel_is_collection = True

        if not toplevel_collection:
            # dataset is based on a data object
            iter = genquery.row_iterator(
                "COLL_NAME, DATA_NAME",
                "META_DATA_ATTR_VALUE = '" + dataset_id + "' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0] + '/' + row[1]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = intake_scan.object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_admin(ctx, actor)
        else:
            # Lock status could not be determined. Assume data object is not locked.
            log.debug(ctx, "Could not determine lock state of data object " + path)
            return False

    log.debug(ctx, 'After check for datasetid - no dataset found')
    return False


def is_coll_in_locked_dataset(ctx, actor, coll):
    """ Check whether given collection is within a locked dataset """
    dataset_id = ''
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dataset_id = row[0]
        log.debug(ctx, 'dataset found: ' + dataset_id)

        # now check whether a lock exists
        # return True

        # Find the toplevel and get the collection check whether is locked
        iter = genquery.row_iterator(
            "COLL_NAME",
            "META_COLL_ATTR_VALUE = '" + dataset_id + "' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
            genquery.AS_LIST, ctx
        )
        toplevel_collection = ''
        toplevel_is_collection = False
        for row in iter:
            toplevel_collection = row[0]
            toplevel_is_collection = True

        if not toplevel_collection:
            # dataset is based on a data object
            iter = genquery.row_iterator(
                "COLL_NAME",
                "META_DATA_ATTR_VALUE = '" + dataset_id + "' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = intake_scan.object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_admin(ctx, actor)
        else:
            # Lock status could not be determined. Assume collection is not locked.
            log.debug(ctx, "Could not determine lock state of data object " + path)
            return False

    log.debug(ctx, 'After check for datasetid - no dataset found')
    return False


def coll_in_path_of_locked_dataset(ctx, actor, coll):
    """ If collection is part of a locked dataset, or holds one on a deeper level, then deletion is not allowed """
    dataset_id = ''
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        dataset_id = row[0]
        log.debug(ctx, 'dataset found: ' + dataset_id)

    if dataset_id:
        # Now find the toplevel and get the collection check whether is locked
        iter = genquery.row_iterator(
            "COLL_NAME",
            "META_COLL_ATTR_VALUE = '" + dataset_id + "' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
            genquery.AS_LIST, ctx
        )
        toplevel_collection = ''
        toplevel_is_collection = False
        for row in iter:
            toplevel_collection = row[0]
            toplevel_is_collection = True

        if not toplevel_collection:
            # dataset is based on a data object
            iter = genquery.row_iterator(
                "COLL_NAME",
                "META_DATA_ATTR_VALUE = '" + dataset_id + "' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/" + user.zone(ctx) + "/home/grp-intake-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = intake_scan.object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_admin(ctx, actor)
        else:
            log.debug(ctx, "Could not determine lock state of data object " + path)
            # Pretend presence of a lock so no unwanted data gets deleted
            return True
    else:
        # No dataset found on indicated collection. Possibly in deeper collections.
        # Can be dataset based upon collection or data object
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME like '" + coll + "%' AND META_COLL_ATTR_NAME in ('to_vault_lock','to_vault_freeze') ",
            genquery.AS_LIST, ctx
        )
        for _row in iter:
            log.debug(ctx, 'Found deeper LOCK')
            # If present there is a lock. No need to further inquire
            return not user.is_admin(ctx, actor)

        # Could be a dataset based on a data object
        iter = genquery.row_iterator(
            "META_DATA_ATTR_VALUE",
            "COLL_NAME like '" + coll + "%' AND META_DATA_ATTR_NAME in ('to_vault_lock','to_vault_freeze') ",
            genquery.AS_LIST, ctx
        )
        for _row in iter:
            log.debug(ctx, 'Found deeper LOCK')
            # If present there is a lock. No need to further inquire
            return not user.is_admin(ctx, actor)

        # There is no lock present
        return False
