# \file      uuReplicate.py
# \brief     Asynchronous replication batch job.
# \author    Chris Smeele
# \copyright Copyright (c) 2020 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import genquery

def uuReplicateBatch(rule_args, callback, rei):
    """Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.
    """
    # (should be the rodsadmin actor)
    uname = session_vars.get_map(rei)['client_user']['user_name']
    uzone = session_vars.get_map(rei)['client_user']['irods_zone']
    actor = uname + '#' + uzone

    for x in genquery.row_iterator(
            "COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE",
            "META_DATA_ATTR_NAME = '{}'".format(UUORGMETADATAPREFIX+'replication_scheduled'),
            genquery.AS_LIST, callback):
        x, y, z = x

        path = x + '/' + y
        try:
            resc_from, resc_to = z.split(',', 1)
        except:
            callback.writeLine('serverLog', 'Scheduled replication of <{}> skipped: bad meta value <{}>'.format(path, z))
            continue

        _replicate_one(callback, actor, path, resc_from, resc_to)


def _replicate_one(callback, actor, path, resc_from, resc_to):
    # Perform scheduled replication for one data object.
    try:
        callback.msiDataObjRepl(path, 'rescName={}++++destRescName={}++++irodsAdmin='
                                      .format(resc_from, resc_to), irods_types.BytesBuf());


    except Exception as e:
        callback.writeLine('serverLog', 'Error: Could not replicate <{}>: {}'.format(path, str(e)))
        return

    # Remove replication_scheduled flag.
    try:
        # Even the sudo msi respects ACLs.
        # Need to set write or own on the object if we don't have it already.
        callback.msiSudoObjAclSet('', 'own', actor, path, '')
        callback.msiSudoObjMetaRemove(path, '-d', '',
                                      UUORGMETADATAPREFIX+'replication_scheduled',
                                      '{},{}'.format(resc_from, resc_to), '', '')

    except Exception as e:
        callback.writeLine('serverLog', 'Error: Could not remove scheduled replication flag from <{}>: {}'.format(path, str(e)))
