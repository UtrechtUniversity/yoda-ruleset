# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from collections import OrderedDict

import genquery
from genquery import AS_DICT, Query

import folder
import meta
import meta_form
from util import *

__all__ = ['api_deposit_create',
           'api_deposit_status',
           'api_deposit_submit',
           'api_deposit_overview',
           'api_deposit_copy_data_package']

DEPOSIT_GROUP = "deposit-pilot"


@api.make()
def api_deposit_copy_data_package(ctx, reference):
    """Create deposit collection and copies selected datapackage into the newly created deposit

    :param ctx:       Combined type of a callback and rei struct
    :param reference: Data Package Reference (UUID4)

    :returns: Path to created deposit collection or API error
    """
    result = deposit_create(ctx)
    if result["deposit_path"] == "not_allowed":
        return api.Error('not_allowed', 'Could not create deposit collection.')

    new_deposit_path = result["deposit_path"]
    coll_target = "/" + user.zone(ctx) + "/home/" + new_deposit_path

    coll_data_package = ""
    iter = genquery.row_iterator(
        "COLL_NAME",
        "META_COLL_ATTR_NAME = '{}' and META_COLL_ATTR_VALUE = '{}'".format(constants.DATA_PACKAGE_REFERENCE, reference),
        genquery.AS_LIST, ctx)

    for row in iter:
        coll_data_package = row[0]

    if coll_data_package == "":
        return api.Error('not_found', 'Could not find data package with provided reference.')

    parts = coll_target.split('/')
    group_name = parts[3]

    # Check if user has READ ACCESS to specific vault package in collection coll_data_package.
    user_full_name = user.full_name(ctx)
    category = meta_form.group_category(ctx, group_name)
    is_datamanager = meta_form.user_is_datamanager(ctx, category, user.full_name(ctx))

    if not is_datamanager:
        # Check if research group has access by checking of research-group exists for this user.
        research_group_access = collection.exists(ctx, coll_data_package)

        if not research_group_access:
            return api.Error('NoPermissions', 'Insufficient rights to perform this action')

    # Check if user has write access to research folder.
    # Only normal user has write access.
    if not meta_form.user_member_type(ctx, group_name, user_full_name) in ['normal', 'manager']:
        return api.Error('NoWriteAccessTargetCollection', 'Not permitted to write in selected folder')

    # Register to delayed rule queue.
    ctx.delayExec(
        "<PLUSET>1s</PLUSET>",
        "iiCopyFolderToResearch('%s', '%s')" % (coll_data_package, coll_target),
        "")

    return {"data": new_deposit_path}


@api.make()
def api_deposit_create(ctx):
    """Create deposit collection through API

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to created deposit collection or API error
    """
    result = deposit_create(ctx)
    if result["deposit_path"] == "not_allowed":
        return api.Error('not_allowed', 'Could not create deposit collection.')
    return {"deposit_path": result["deposit_path"]}


def deposit_create(ctx):
    """Create deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to created deposit collection
    """
    coll = "/" + user.zone(ctx) + "/home/" + DEPOSIT_GROUP
    datapackage_name = pathutil.basename(coll)

    if len(datapackage_name) > 235:
        datapackage_name = datapackage_name[0:235]

    ret = msi.get_icat_time(ctx, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    # Ensure deposit target does not exist.
    i = 0
    target_base = coll + "/" + datapackage_name + "[" + timestamp + "]"
    deposit_path = target_base
    while collection.exists(ctx, deposit_path):
        i += 1
        deposit_path = target_base + "[" + str(i) + "]"

    # Try to create deposit collection.
    try:
        collection.create(ctx, deposit_path)
    except msi.CollCreateError:
        return {"deposit_path": "not_allowed"}

    space, zone, group, subpath = pathutil.info(deposit_path)
    deposit_path = "{}/{}".format(group, subpath)

    return {"deposit_path": deposit_path}


@api.make()
def api_deposit_status(ctx, path):
    """Retrieve status of deposit.

    :param ctx: Combined type of a callback and rei struct
    :param path: Path to deposit collection

    :returns: Deposit status
    """
    coll = "/{}/home{}".format(user.zone(ctx), path)
    if not collection.exists(ctx, coll):
        return api.Error('nonexistent', 'Deposit collection does not exist.')

    meta_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    data = False
    if not collection.empty(ctx, coll):
        if collection.data_count(ctx, coll) == 1 and data_object.exists(ctx, meta_path):
            # Only file is yoda-metadata.json.
            data = False
        else:
            data = True

    metadata = False
    if data_object.exists(ctx, meta_path) and meta.is_json_metadata_valid(ctx, meta_path):
        metadata = True

    return {"data": data, "metadata": metadata}


@api.make()
def api_deposit_submit(ctx, path):
    """Submit deposit collection.

    :param ctx: Combined type of a callback and rei struct
    :param path: Path to deposit collection

    :returns: API status
    """
    coll = "/{}/home{}".format(user.zone(ctx), path)
    if not collection.exists(ctx, coll):
        return api.Error('nonexistent', 'Deposit collection does not exist.')

    return folder.set_status(ctx, coll, constants.research_package_state.SUBMITTED)


@api.make()
def api_deposit_overview(ctx,
                         coll='/',
                         sort_on='name',
                         sort_order='asc',
                         offset=0,
                         limit=10,
                         space=pathutil.Space.OTHER.value):
    """Get paginated collection contents, including size/modify date information.

    This function browses a folder and only looks at the collections in it. No dataobjects.
    Specifically for deposit selection which is why it adds deposit-specific data to the result

    :param ctx:        Combined type of a callback and rei struct
    :param coll:       Collection to get paginated contents of
    :param sort_on:    Column to sort on ('name', 'modified' or size)
    :param sort_order: Column sort order ('asc' or 'desc')
    :param offset:     Offset to start browsing from
    :param limit:      Limit number of results
    :param space:      Space the collection is in

    :returns: Dict with paginated collection contents
    """
    def transform(row):
        # Remove ORDER_BY etc. wrappers from column names.
        x = {re.sub('.*\((.*)\)', '\\1', k): v for k, v in row.items()}

        deposit_size = collection.size(ctx, x['COLL_NAME'])

        deposit_title = '(no title)'
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'Title'".format(x['COLL_NAME']),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            deposit_title = row[0]

        deposit_access = ''
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'Data_Access_Restriction'".format(x['COLL_NAME']),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            deposit_access = row[0].split("-")[0].strip()

        return {'name':          x['COLL_NAME'].split('/')[-1],
                'type':          'coll',
                'modify_time':   int(x['COLL_MODIFY_TIME']),
                'deposit_title': deposit_title,
                'deposit_access': deposit_access,
                'deposit_size':  deposit_size}

    if sort_on == 'modified':
        # FIXME: Sorting on modify date is borked: There appears to be no
        # reliable way to filter out replicas this way - multiple entries for
        # the same file may be returned when replication takes place on a
        # minute boundary, for example.
        # We would want to take the max modify time *per* data name.
        # (or not? replication may take place a long time after a modification,
        #  resulting in a 'too new' date)
        ccols = ['COLL_NAME', 'ORDER(COLL_MODIFY_TIME)']
    elif sort_on == 'size':
        ccols = ['COLL_NAME', 'COLL_MODIFY_TIME']
    else:
        ccols = ['ORDER(COLL_NAME)', 'COLL_MODIFY_TIME']

    if sort_order == 'desc':
        ccols = [x.replace('ORDER(', 'ORDER_DESC(') for x in ccols]

    zone = user.zone(ctx)

    # We make offset/limit act on two queries at once, placing qdata right after qcoll.
    qcoll = Query(ctx, ccols,
                  "COLL_PARENT_NAME = '{}' AND COLL_NAME not like '/{}/home/vault-%' AND COLL_NAME not like '/{}/home/grp-vault-%'".format(coll, zone, zone),
                  offset=offset, limit=limit, output=AS_DICT)
    colls = map(transform, list(qcoll))

    if len(colls) == 0:
        # No results at all?
        # Make sure the collection actually exists.
        if not collection.exists(ctx, coll):
            return api.Error('nonexistent', 'The given path does not exist')
        # (checking this beforehand would waste a query in the most common situation)

    return OrderedDict([('total', qcoll.total_rows()),
                        ('items', colls)])
