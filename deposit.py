# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from collections import OrderedDict

from genquery import AS_DICT, Query
import genquery


import folder
import meta
from util import *

__all__ = ['api_deposit_create',
           'api_deposit_status',
           'api_deposit_submit',
           'api_deposit_browse_collections']

DEPOSIT_GROUP = "deposit-pilot"


@api.make()
def api_deposit_browse_collections(ctx,
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

        deposit_count = collection.data_count(ctx, x['COLL_NAME'])
        deposit_size = collection.size(ctx, x['COLL_NAME'])

        deposit_title = '[No title]'
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'Title'".format(x['COLL_NAME']),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            deposit_title = row[0]

        return {'name':        x['COLL_NAME'].split('/')[-1],
                'type':        'coll',
                'modify_time': int(x['COLL_MODIFY_TIME']),
                'deposit_title': deposit_title,
                'deposit_count': deposit_count,
                'deposit_size': deposit_size}

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


def determine_deposit_path(ctx):
    """Determine deposit path for a user."""
    coll = "/" + user.zone(ctx) + "/home/" + DEPOSIT_GROUP
    datapackage_name = pathutil.basename(coll)

    if len(datapackage_name) > 235:
        datapackage_name = datapackage_name[0:235]

    ret = msi.get_icat_time(ctx, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    # Ensure vault target does not exist.
    i = 0
    target_base = coll + "/" + datapackage_name + "[" + timestamp + "]"
    deposit_path = target_base
    while collection.exists(ctx, deposit_path):
        i += 1
        deposit_path = target_base + "[" + str(i) + "]"

    collection.create(ctx, deposit_path)

    space, zone, group, subpath = pathutil.info(deposit_path)

    return "{}/{}".format(group, subpath)


@api.make()
def api_deposit_create(ctx):
    """Create deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to created deposit collection
    """

    return {"deposit_path": determine_deposit_path(ctx)}


@api.make()
def api_deposit_status(ctx, path):
    """Retrieve status of deposit.

    :param ctx: Combined type of a callback and rei struct
    :param path: Path to deposit collection

    :returns: Deposit status
    """
    coll = "/{}/home{}".format(user.zone(ctx), path)
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
    return folder.set_status(ctx, coll, constants.research_package_state.SUBMITTED)
