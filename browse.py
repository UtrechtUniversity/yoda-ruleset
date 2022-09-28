# -*- coding: utf-8 -*-
"""Functions for listing collection information."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from collections import OrderedDict

from genquery import AS_DICT, Query

from util import *

__all__ = ['api_browse_folder',
           'api_browse_collections',
           'api_search']


@api.make()
def api_browse_folder(ctx,
                      coll='/',
                      sort_on='name',
                      sort_order='asc',
                      offset=0,
                      limit=10,
                      space=pathutil.Space.OTHER.value):
    """Get paginated collection contents, including size/modify date information.

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
        if 'DATA_NAME' in x and 'META_DATA_ATTR_VALUE' in x:
            return {x['DATA_NAME']: x['META_DATA_ATTR_VALUE']}
        elif 'DATA_NAME' in x:
            return {'name':        x['DATA_NAME'],
                    'type':        'data',
                    'size':        int(x['DATA_SIZE']),
                    'modify_time': int(x['DATA_MODIFY_TIME']),
                    'state':       'REG'}
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

    zone = user.zone(ctx)

    # We make offset/limit act on two queries at once, placing qdata right after qcoll.
    if space == str(pathutil.Space.RESEARCH):
        qcoll = Query(ctx, ccols,
                      "COLL_PARENT_NAME = '{}' AND COLL_NAME not like '/{}/home/vault-%' AND COLL_NAME not like '/{}/home/grp-vault-%'".format(coll, zone, zone),
                      offset=offset, limit=limit, output=AS_DICT)
    elif space == str(pathutil.Space.VAULT):
        qcoll = Query(ctx, ccols,
                      "COLL_PARENT_NAME = '{}' AND COLL_NAME like '/{}/home/%vault-%'".format(coll, zone),
                      offset=offset, limit=limit, output=AS_DICT)
    else:
        qcoll = Query(ctx, ccols, "COLL_PARENT_NAME = '{}'".format(coll),
                      offset=offset, limit=limit, output=AS_DICT)

    colls = list(map(transform, list(qcoll)))

    qdata = Query(ctx, dcols, "COLL_NAME = '{}'".format(coll),
                  offset=max(0, offset - qcoll.total_rows()), limit=limit - len(colls), output=AS_DICT)
    datas = list(map(transform, list(qdata)))

    if len(colls) + len(datas) == 0:
        # No results at all?
        # Make sure the collection actually exists.
        if not collection.exists(ctx, coll):
            return api.Error('nonexistent', 'The given path does not exist')
        # (checking this beforehand would waste a query in the most common situation)

    if config.enable_tape_archive:
        # Retrieve tape archive state for data objects.
        state_cols = ['DATA_NAME', 'META_DATA_ATTR_VALUE']
        qstate = Query(ctx, state_cols, "COLL_NAME = '{}' AND META_DATA_ATTR_NAME = '{}'".format(coll, "org_tape_archive_state"),
                       offset=max(0, offset - qcoll.total_rows()), limit=limit - len(colls), output=AS_DICT)
        state = map(transform, list(qstate))

        for d in datas:
            name = d['name']
            if any(name in s for s in state):
                for s in state:
                    if name in s:
                        d.update({'state': s[name]})

    return OrderedDict([('total', qcoll.total_rows() + qdata.total_rows()),
                        ('items', colls + datas)])


@api.make()
def api_browse_collections(ctx,
                           coll='/',
                           sort_on='name',
                           sort_order='asc',
                           offset=0,
                           limit=10,
                           space=pathutil.Space.OTHER.value):
    """Get paginated collection contents, including size/modify date information.

    This function browses a folder and only looks at the collections in it. No dataobjects.
    Specifically for folder selection for copying data to research area from vault for instance.

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
    elif sort_on == 'size':
        ccols = ['COLL_NAME', 'COLL_MODIFY_TIME']
    else:
        ccols = ['ORDER(COLL_NAME)', 'COLL_MODIFY_TIME']

    if sort_order == 'desc':
        ccols = [x.replace('ORDER(', 'ORDER_DESC(') for x in ccols]

    zone = user.zone(ctx)

    # We make offset/limit act on two queries at once, placing qdata right after qcoll.
    if space == str(pathutil.Space.RESEARCH):
        qcoll = Query(ctx, ccols,
                      "COLL_PARENT_NAME = '{}' AND COLL_NAME not like '/{}/home/vault-%' AND COLL_NAME not like '/{}/home/grp-vault-%'".format(coll, zone, zone),
                      offset=offset, limit=limit, output=AS_DICT)
    elif space == str(pathutil.Space.VAULT):
        qcoll = Query(ctx, ccols,
                      "COLL_PARENT_NAME = '{}' AND COLL_NAME like '/{}/home/%vault-%'".format(coll, zone),
                      offset=offset, limit=limit, output=AS_DICT)
    else:
        qcoll = Query(ctx, ccols, "COLL_PARENT_NAME = '{}'".format(coll),
                      offset=offset, limit=limit, output=AS_DICT)

    colls = list(map(transform, list(qcoll)))

    if len(colls) == 0:
        # No results at all?
        # Make sure the collection actually exists.
        if not collection.exists(ctx, coll):
            return api.Error('nonexistent', 'The given path does not exist')
        # (checking this beforehand would waste a query in the most common situation)

    return OrderedDict([('total', qcoll.total_rows()),
                        ('items', colls)])


@api.make()
def api_search(ctx,
               search_string,
               search_type='filename',
               sort_on='name',
               sort_order='asc',
               offset=0,
               limit=10):
    """Get paginated search results, including size/modify date/location information.

    :param ctx:           Combined type of a callback and rei struct
    :param search_string: String used to search
    :param search_type:   Search type ('filename', 'folder', 'metadata', 'status')
    :param sort_on:       Column to sort on ('name', 'modified' or size)
    :param sort_order:    Column sort order ('asc' or 'desc')
    :param offset:        Offset to start browsing from
    :param limit:         Limit number of results

    :returns: Dict with paginated search results
    """
    def transform(row):
        # Remove ORDER_BY etc. wrappers from column names.
        x = {re.sub('.*\((.*)\)', '\\1', k): v for k, v in row.items()}

        if 'DATA_NAME' in x:
            _, _, path, subpath = pathutil.info(x['COLL_NAME'])
            if subpath != '':
                path = path + "/" + subpath

            return {'name':        "/{}/{}".format(path, x['DATA_NAME']),
                    'type':        'data',
                    'size':        int(x['DATA_SIZE']),
                    'modify_time': int(x['DATA_MODIFY_TIME'])}

        if 'COLL_NAME' in x:
            _, _, path, subpath = pathutil.info(x['COLL_NAME'])
            if subpath != '':
                path = path + "/" + subpath

            return {'name':        "/{}".format(path),
                    'type':        'coll',
                    'modify_time': int(x['COLL_MODIFY_TIME'])}

    # Replace, %, _ and \ since iRODS does not handle those correctly.
    # HdR this can only be done in a situation where search_type is NOT status!
    # Status description must be kept in tact.
    if not search_type == 'status':
        search_string = search_string.replace("\\", "\\\\")
        search_string = search_string.replace("%", "\%")
        search_string = search_string.replace("_", "\_")

    zone = user.zone(ctx)

    query_is_case_sensitive = False
    if search_type == 'filename':
        cols = ['ORDER(DATA_NAME)', 'COLL_NAME', 'MIN(DATA_CREATE_TIME)', 'MAX(DATA_MODIFY_TIME)', 'DATA_SIZE']
        where = "COLL_NAME like '{}%%' AND DATA_NAME like '%%{}%%'".format("/" + zone + "/home", search_string)
    elif search_type == 'folder':
        cols = ['ORDER(COLL_NAME)', 'COLL_PARENT_NAME', 'MIN(COLL_CREATE_TIME)', 'MAX(COLL_MODIFY_TIME)']
        where = "COLL_PARENT_NAME like '{}%%' AND COLL_NAME like '%%{}%%'".format("/" + zone + "/home", search_string)
    elif search_type == 'metadata':
        cols = ['ORDER(COLL_NAME)', 'MIN(COLL_CREATE_TIME)', 'MAX(COLL_MODIFY_TIME)']
        where = "META_COLL_ATTR_UNITS like '{}%%' AND META_COLL_ATTR_VALUE like '%%{}%%' AND COLL_NAME like '{}%%'".format(
                constants.UUUSERMETADATAROOT + "_", search_string, "/" + zone + "/home"
        )
    elif search_type == 'status':
        query_is_case_sensitive = True
        status = search_string.split(":")
        status_value = status[1]
        if status[0] == "research":
            status_name = constants.IISTATUSATTRNAME
        else:
            status_name = constants.IIVAULTSTATUSATTRNAME

        cols = ['ORDER(COLL_NAME)', 'MIN(COLL_CREATE_TIME)', 'MAX(COLL_MODIFY_TIME)']
        where = "META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}' AND COLL_NAME like '{}%%'".format(
                status_name, status_value, "/" + zone + "/home"
        )

    if sort_order == 'desc':
        cols = [x.replace('ORDER(', 'ORDER_DESC(') for x in cols]

    qdata = Query(ctx, cols, where, offset=max(0, int(offset)),
                  limit=int(limit), case_sensitive=query_is_case_sensitive, output=AS_DICT)

    datas = map(transform, list(qdata))

    return OrderedDict([('total', qdata.total_rows()),
                        ('items', datas)])
