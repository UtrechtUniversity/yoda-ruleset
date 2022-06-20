# -*- coding: utf-8 -*-
"""Functions for replication management."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import datetime
import os
import time

import genquery
import irods_types

import folder
import meta_form
from util import *

__all__ = ['rule_replication_batch']


def replicate_asynchronously(ctx, path, source_resource, target_resource):
    """ Mark data object for batch replication by setting 'org_replication_scheduled' metadata.

    Give rods 'own' access so that they can remove the AVU.

    :param[in] path:              data object to be replicated
    :param[in] source_resource    resource to be used as source
    :param[in] target_resource    resource to be used as destination
    """
    msi.set_acl(ctx, "default", "own", "rods#{}".format(zone), path)
    avu.set_on_data(ctx, path, constants.UUORGMETADATAPREFIX + "replication_scheduled", "{},{}".format(source_resource, target_resource))


@rule.make(inputs=range(4), outputs=range(4, 5))
def rule_replication_batch(ctx, verbose, data_id, max_batch_size, delay):
    """ Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.

    :param verbose:        Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    :param data_id:        The start id to be searching from for new data objects
    :param max_batch_size: Max amount of accumulated data sizes to be handled in one batch
    :param delay:          The delay time before a new batch job is kicked off

    :returns: String with status of the batch process
    """
    bucket = 0
    count        = 0
    count_ok      = 0
    print_verbose = (verbose == '1')
    zone = user.zone(ctx)

    attr = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "replication_failed"

    # Get list of data objects scheduled for replication => only user First??
    iter = genquery.row_iterator(
        "ORDER(DATA_ID), COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE, DATA_SIZE",
        "META_DATA_ATTR_NAME = '{}' AND DATA_ID >='{}'".format(attr, int(data_id)),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # Stop further execution if admin has blocked replication process
        if is_replication_blocked_by_admin(ctx, zone):
            log.write(ctx, "[replication] Batch replication job is stopped through admin interference")
            return '[replication] Batch replication job is stopped'

        count += 1
        path = row[1] + "/" + row[2]
        rescs = row[3]
        xs = rescs.split(',')
        if len(xs) is not 2:
            # not replicable
            avu.set_on_data(ctx, path, errorattr, "true")
            log.write(ctx, "[replication] ERROR - Invalid replication data for {}".format(path))
            # Go to next record and skip further processing
            continue

        from = xs[0]
        to = xs[1]

        if print_verbose:
            log.write(ctx, "[replication] Batch replication: copying  copying {} from {} to {} ...".format(path, from, to))

        # Actual replication
        try:
            # Workaround the PREP deadlock issue: Restrict threads to 1.
            ofFlags = "forceFlag=++++numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(from, to)
            msi.data_obj_repl(ctx, path, ofFlags, irods_types.BytesBuf())
            # Mark as correctly replicated
            count_ok += 1
        except msi.Error as e:
            log.write(ctx, '[replication] ERROR - The file could not be replicated: {}'.format(str(e)))
            avu.set_on_data(ctx, path, errorattr, "true")

        # Remove replication_scheduled flag no matter if replication succeeded or not.
        # rods should have been given own access via policy to allow AVU changes
        avu_deleted = False
        try:
            avu.rmw_from_data(ctx, path, attr, "%")  # use wildcard cause rm_from_data causes problems
            avu_deleted = True
        except Exception:
            avu_deleted = False

        # Try removing attr/resc meta data again with other ACL's
        if not avu_deleted:
            try:
                # The object's ACLs may have changed.
                # Force the ACL and try one more time.
                msi.sudo_obj_acl_set(ctx, "", "own", user.full_name(ctx), path, "")
                avu.rmw_from_data(ctx, path, attr, "%")  # use wildcard cause rm_from_data causes problems
            except Exception:
                # error => report it but still continue
                log.write(ctx, "[replication] ERROR - Scheduled replication of <{}>: could not remove schedule flag".format(path))

        # Determine new bucket
        bucket += int(row[4])

        # max_batch_size exceeded -> then stopp current batch and kickoff the next one through a delayed rule
        if bucket >= int(max_batch_size):
            # Kickoff the next batch
            log.write(ctx, "[replication] Batch replication job partly finished. {}/{} objects succesfully replicated.".format(count_ok, count))

            # Set off the next batch from correct starting point
            data_id = int(row[0]) + 1
            # ?? Dit moet nog de PYTHON variant worden
            ctx.delayExec(
                "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % int(delay),
                "rule_replication_batch('%s', '%d', '%d', '%d')" % (verbose, data_id, int(max_batch_size), int(delay)),
                "")
            # break out of the iteration as max_batch_size has been exceeded
            return '[replication] New batch initiated'

    # Total replication process completed
    log.write(ctx, "[replication] Batch replication job finished. {}/{} objects succesfully replicated.".format(count_ok, count))


def is_replication_blocked_by_admin(ctx, zone):
    """ Admin can put the replication process on a hold by adding a file called 'stop_replication' in collection /yoda/flags """
    iter = genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME = '" + "/{}/yoda/flags".format(zone) + "' AND DATA_NAME = 'stop_replication'",
        genquery.AS_LIST, ctx
    )
    return (len(iter)>0)
