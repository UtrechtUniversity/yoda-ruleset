# -*- coding: utf-8 -*-
"""Functions for listing collection information"""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from collections import OrderedDict

import re
import genquery
import irods_types

from util import *
from util.query import Query

__all__ = ['api_uu_browse_folder']


@api.make()
def api_uu_browse_folder(ctx,
                         coll='/',
                         sort_on='name',
                         sort_order='asc',
                         offset=0,
                         limit=10):
    """Gets paginated collection contents, including size/modify date information."""

    def transform(row):
        # Remove ORDER_BY etc. wrappers from column names.
        x = {re.sub('.*\((.*)\)', '\\1', k): v for k, v in row.items()}

        if 'DATA_NAME' in x:
            return {'name':        x['DATA_NAME'],
                    'type':        'data',
                    'size':        int(x['DATA_SIZE']),
                    'modify_time': int(x['DATA_MODIFY_TIME'])}
        else:
            return {'name':        x['COLL_NAME'].split('/')[-1],
                    'type':        'coll',
                    'modify_time': int(x['COLL_MODIFY_TIME'])}

    if sort_on == 'modified':
        # FIXME: Sorting on modify date is borked: There appears to be no
        # reliable way to filter out replicas this way - multiple entries for
        # the same file may be returned when replication takes place on a
        # minute boundary, for example.
        # We would want to take the max modify time *per* data name.
        # (or not? replication may take place a long time after a modification,
        #  resulting in a 'too new' date)
        ccols = ['COLL_NAME', 'ORDER(COLL_MODIFY_TIME)']
        dcols = ['DATA_NAME', 'MIN(DATA_CREATE_TIME)', 'ORDER(DATA_MODIFY_TIME)', 'DATA_SIZE']
    elif sort_on == 'size':
        ccols = ['COLL_NAME', 'COLL_MODIFY_TIME']
        dcols = ['DATA_NAME', 'MIN(DATA_CREATE_TIME)', 'MAX(DATA_MODIFY_TIME)', 'ORDER(DATA_SIZE)']
    else:
        ccols = ['ORDER(COLL_NAME)', 'COLL_MODIFY_TIME']
        dcols = ['ORDER(DATA_NAME)', 'MIN(DATA_CREATE_TIME)', 'MAX(DATA_MODIFY_TIME)', 'DATA_SIZE']

    if sort_order == 'desc':
        ccols = [x.replace('ORDER(', 'ORDER_DESC(') for x in ccols]
        dcols = [x.replace('ORDER(', 'ORDER_DESC(') for x in dcols]

    # We make offset/limit act on two queries at once, placing qdata right after qcoll.
    qcoll = Query(ctx, ccols, "COLL_PARENT_NAME = '{}'".format(coll), offset=offset, limit=limit)
    qdata = Query(ctx, dcols, "COLL_NAME = '{}'".format(coll),
                  offset=max(0, offset - qcoll.total_rows()), limit=limit - len(qcoll))

    colls = map(transform, list(qcoll))
    datas = map(transform, list(qdata))

    if len(colls) + len(datas) == 0:
        # No results at all?
        # Make sure the collection actually exists.
        if not collection.exists(ctx, coll):
            return api.Error('nonexistent', 'The given path does not exist')
        # (checking this beforehand would waste a query in the most common situation)

    return OrderedDict([('total', qcoll.total_rows() + qdata.total_rows()),
                        ('items', colls + datas)])
