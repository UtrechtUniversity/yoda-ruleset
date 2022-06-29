# -*- coding: utf-8 -*-
"""Functions for replication management."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import irods_types

from util import *

__all__ = ['rule_replication_batch']


def replicate_asynchronously(ctx, path, source_resource, target_resource):
    """Schedule replication of a data object.

    :param ctx:             Combined type of a callback and rei struct
    :param path:            Data object to be replicated
    :param source_resource: Resource to be used as source
    :param target_resource: Resource to be used as destination
    """
    zone = user.zone(ctx)

    # Give rods 'own' access so that they can remove the AVU.
    msi.set_acl(ctx, "default", "own", "rods#{}".format(zone), path)

    # Mark data object for batch replication by setting 'org_replication_scheduled' metadata.
    avu.set_on_data(ctx, path, constants.UUORGMETADATAPREFIX + "replication_scheduled", "{},{}".format(source_resource, target_resource))


@rule.make()
def rule_replicate_batch(ctx, verbose):
    """Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.

    :param ctx:     Combined type of a callback and rei struct
    :param verbose: Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    """
    count         = 0
    count_ok      = 0
    print_verbose = (verbose == '1')

    attr = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "replication_failed"

    if is_replication_blocked_by_admin(ctx):
        log.write(ctx, "[replication] Batch replication job is stopped")
    else:
        log.write(ctx, "[replication] Batch replication job started")

        # Get list of data objects scheduled for replication.
        iter = genquery.row_iterator(
            "ORDER(DATA_ID), COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE",
            "META_DATA_ATTR_NAME = '{}' AND DATA_ID >='{}'".format(attr, int(data_id)),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            # Stop further execution if admin has blocked replication process.
            if is_replication_blocked_by_admin(ctx):
                log.write(ctx, "[replication] Batch replication job is stopped")
                break

            count += 1
            path = row[1] + "/" + row[2]
            rescs = row[3]
            xs = rescs.split(',')
            if len(xs) != 2:
                # not replicable
                avu.set_on_data(ctx, path, errorattr, "true")
                log.write(ctx, "[replication] ERROR - Invalid replication data for {}".format(path))
                # Go to next record and skip further processing
                continue

            from_path = xs[0]
            to_path = xs[1]

            if print_verbose:
                log.write(ctx, "[replication] Batch replication: copying  copying {} from {} to {}".format(path, from_path, to_path))

            # Actual replication
            try:
                # Workaround the PREP deadlock issue: Restrict threads to 1.
                ofFlags = "forceFlag=++++numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(from_path, to_path)
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

        # Total replication process completed
        log.write(ctx, "[replication] Batch replication job finished. {}/{} objects succesfully replicated.".format(count_ok, count))


def is_replication_blocked_by_admin(ctx):
    """Admin can put the replication process on a hold by adding a file called 'stop_replication' in collection /yoda/flags.

    :param ctx: Combined type of a callback and rei struct

    :returns: Boolean indicating if admin put replication on hold.
    """
    zone = user.zone(ctx)
    iter = genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME = '" + "/{}/yoda/flags".format(zone) + "' AND DATA_NAME = 'stop_replication'",
        genquery.AS_LIST, ctx
    )
    return len(iter) > 0
