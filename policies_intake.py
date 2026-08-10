"""Policies for intake."""

__copyright__ = 'Copyright (c) 2021-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
from tstrings import t

from util import *


def object_is_locked(ctx: rule.Context, path: str, is_collection: bool) -> dict:
    """Returns whether given object in path (collection or dataobject) is locked or frozen

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to object or collection
    :param is_collection: Whether path contains a collection or data object

    :returns: Returns locked state
    """
    locked_state = {"locked": False,
                    "frozen": False}

    if is_collection:
        iter = genquery.row_iterator(
            "META_COLL_ATTR_NAME",
            t("COLL_NAME = '{path}'"),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            if row[0] in ['to_vault_lock', 'to_vault_freeze']:
                locked_state['locked'] = True
                if row[0] == 'to_vault_freeze':
                    locked_state['frozen'] = True
    else:
        parent_coll = pathutil.dirname(path)  # noqa F841
        iter = genquery.row_iterator(
            "META_DATA_ATTR_NAME",
            t("COLL_NAME = '{parent_coll}' AND DATA_NAME = '{pathutil.basename(path)}'"),
            genquery.AS_LIST, ctx
        )
        # return locked_state
        for row in iter:
            if row[0] in ['to_vault_lock', 'to_vault_freeze']:
                locked_state['locked'] = True
                if row[0] == 'to_vault_freeze':
                    locked_state['frozen'] = True

    return locked_state


def is_data_in_locked_dataset(ctx: rule.Context, actor: str, path: str) -> bool:
    """ Check whether given data object is within a locked dataset """
    dataset_id = ''
    coll = pathutil.chop(path)[0]
    data_name = pathutil.chop(path)[1]  # noqa F841
    intake_group_prefix = _get_intake_group_prefix(coll)

    # look for DATA based info first.
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        t("DATA_NAME = '{data_name}' AND META_DATA_ATTR_NAME = 'dataset_id' AND COLL_NAME = '{coll}'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dataset_id = row[0]
        log.debug(ctx, 'DATA - dataset found: ' + dataset_id)

    if not dataset_id:
        # look for COLL based info
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            t("META_COLL_ATTR_NAME = 'dataset_id' AND COLL_NAME = '{coll}' "),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            dataset_id = row[0]
            log.debug(ctx, 'COLL - dataset found: ' + dataset_id)

    if dataset_id:
        # now check whether a lock exists
        # Find the toplevel and get the collection check whether is locked
        iter = genquery.row_iterator(
            "COLL_NAME",
            f"META_COLL_ATTR_VALUE = '{dataset_id}' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
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
                f"META_DATA_ATTR_VALUE = '{dataset_id}' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0] + '/' + row[1]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_rodsadmin(ctx, actor)
        else:
            # Lock status could not be determined. Assume data object is not locked.
            log.debug(ctx, "Could not determine lock state of data object " + path)
            return False

    log.debug(ctx, 'After check for datasetid - no dataset found')
    return False


def is_coll_in_locked_dataset(ctx: rule.Context, actor: str, coll: str) -> bool:
    """ Check whether given collection is within a locked dataset """
    dataset_id = ''
    intake_group_prefix = _get_intake_group_prefix(coll)

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = 'dataset_id'"),
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
            f"META_COLL_ATTR_VALUE = '{dataset_id}' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
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
                f"META_DATA_ATTR_VALUE = '{dataset_id}' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_rodsadmin(ctx, actor)
        else:
            # Lock status could not be determined. Assume collection is not locked.
            log.debug(ctx, "Could not determine lock state of data object " + coll)
            return False

    log.debug(ctx, 'After check for datasetid - no dataset found')
    return False


def coll_in_path_of_locked_dataset(ctx: rule.Context, actor: str, coll: str) -> bool:
    """ If collection is part of a locked dataset, or holds one on a deeper level, then deletion is not allowed """
    dataset_id = ''
    intake_group_prefix = _get_intake_group_prefix(coll)

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = 'dataset_id'"),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        dataset_id = row[0]
        log.debug(ctx, 'dataset found: ' + dataset_id)

    if dataset_id:
        # Now find the toplevel and get the collection check whether is locked
        iter = genquery.row_iterator(
            "COLL_NAME",
            f"META_COLL_ATTR_VALUE = '{dataset_id}' AND META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
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
                f"META_DATA_ATTR_VALUE = '{dataset_id}' AND  META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '/{user.zone(ctx)}/home/{intake_group_prefix}-%'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                toplevel_collection = row[0]
                toplevel_is_collection = False

        if toplevel_collection:
            locked_state = object_is_locked(ctx, toplevel_collection, toplevel_is_collection)
            log.debug(ctx, locked_state)
            return (locked_state['locked'] or locked_state['frozen']) and not user.is_rodsadmin(ctx, actor)
        else:
            log.debug(ctx, "Could not determine lock state of data object " + coll)
            # Pretend presence of a lock so no unwanted data gets deleted
            return True
    else:
        # No dataset found on indicated collection. Possibly in deeper collections.
        # Can be dataset based upon collection or data object
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            t("COLL_NAME like '{coll}%' AND META_COLL_ATTR_NAME in ('to_vault_lock','to_vault_freeze')"),
            genquery.AS_LIST, ctx
        )
        for _row in iter:
            log.debug(ctx, 'Found deeper LOCK')
            # If present there is a lock. No need to further inquire
            return not user.is_rodsadmin(ctx, actor)

        # Could be a dataset based on a data object
        iter = genquery.row_iterator(
            "META_DATA_ATTR_VALUE",
            t("COLL_NAME like '{coll}%' AND META_DATA_ATTR_NAME in ('to_vault_lock','to_vault_freeze')"),
            genquery.AS_LIST, ctx
        )
        for _row in iter:
            log.debug(ctx, 'Found deeper LOCK')
            # If present there is a lock. No need to further inquire
            return not user.is_rodsadmin(ctx, actor)

        # There is no lock present
        return False


def _get_intake_group_prefix(coll: str) -> str:
    """ Get the group prefix of a intake collection name: 'grp-intake' or 'intake' """
    parts = coll.split('/')[3].split('-')
    del parts[-1]
    return '-'.join(parts)
