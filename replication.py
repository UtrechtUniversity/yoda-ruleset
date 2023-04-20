# -*- coding: utf-8 -*-
"""Functions for replication management."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import random

import genquery
import irods_types

from util import *

__all__ = ['rule_replicate_batch']


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
    try:
        # Add random id for replication balancing purposes
        ctx.msi_add_avu('-d', path, constants.UUORGMETADATAPREFIX + "replication_scheduled", "{},{},{}".format(source_resource, target_resource, random.randint(1, 64)), "")
    except Exception:
        pass


@rule.make()
def rule_replicate_batch(ctx, verbose, balance_id_min, balance_id_max):
    """Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.

    For load balancing purposes each data object has been randomly assigned a number (balance_id) between 1-64.
    To enable efficient parallel batch processing, each batch job gets assigned a range of numbers. For instance 1-32.
    The corresponding job will only process data objets with a balance id within the range.

    :param ctx:            Combined type of a callback and rei struct
    :param verbose:        Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    :param balance_id_min: Minimum balance id for batch jobs (value 1-64)
    :param balance_id_max: Maximum balance id for batch jobs (value 1-64)

    """
    count         = 0
    count_ok      = 0
    print_verbose = (verbose == '1')

    attr = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "replication_failed"

    # Stop further execution if admin has blocked replication process.
    if is_replication_blocked_by_admin(ctx):
        log.write(ctx, "Batch replication job is stopped")
    else:
        log.write(ctx, "Batch replication job started - balance id: {}-{}".format(balance_id_min, balance_id_max))

        # Get list up to 1000 data objects scheduled for replication.
        iter = list(genquery.Query(ctx,
                    ['ORDER(DATA_ID)', 'COLL_NAME', 'DATA_NAME', 'META_DATA_ATTR_VALUE', 'DATA_RESC_NAME'],
                    "META_DATA_ATTR_NAME = '{}'".format(attr),
                    offset=0, limit=1000, output=genquery.AS_LIST))
        for row in iter:
            # Stop further execution if admin has blocked replication process.
            if is_replication_blocked_by_admin(ctx):
                log.write(ctx, "Batch replication job is stopped")
                break

            path = row[1] + "/" + row[2]

            # Metadata value contains from_path, to_path and balace id for load balancing purposes.
            info = row[3].split(',')
            from_path = info[0]
            to_path = info[1]

            # Backwards compatability with replication metadata created in v1.8 or earlier.
            backwards_compatibility = False

            if len(info) == 3:
                balance_id = int(info[2])
            elif len(info) == 2:
                backwards_compatibility = True
                balance_id = int(balance_id_min)
            else:
                # Not replicable.
                log.write(ctx, "ERROR - Invalid replication data for {}".format(path))
                try:
                    ctx.msi_add_avu('-d', path, errorattr, "Invalid,Invalid", "")
                except Exception:
                    pass

                # Go to next record and skip further processing.
                continue

            # Check whether balance id is within the range for this job
            if balance_id < int(balance_id_min) or balance_id > int(balance_id_max):
                # Skip this one and go to the next data object to be replicated.
                if print_verbose:
                    log.write(ctx, "Batch replication: skipping {} due to load balancing: range {} {}".format(path, balance_id_min, balance_id_max))
                continue

            # For totalization only count the dataobjects that are within the specified balancing range
            count += 1
            data_resc_name = row[4]

            if print_verbose:
                log.write(ctx, "Batch replication: copying {} from {} to {}".format(path, from_path, to_path))

            # Actual replication
            try:
                try:
                    # Ensure first replica has checksum before replication.
                    msi.data_obj_chksum(ctx, path, "", irods_types.BytesBuf())
                except Exception:
                    pass

                # Workaround the PREP deadlock issue: Restrict threads to 1.
                ofFlags = "numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(from_path, to_path)
                msi.data_obj_repl(ctx, path, ofFlags, irods_types.BytesBuf())
                # Mark as correctly replicated
                count_ok += 1
            except msi.Error as e:
                log.write(ctx, 'ERROR - The file could not be replicated: {}'.format(str(e)))

                if print_verbose:
                    log.write(ctx, "Batch replication retry: copying {} from {} to {}".format(path, data_resc_name, to_path))

                # Retry replication with data resource name (covers case where resource is removed from the resource hierarchy).
                try:
                    log.write(ctx, 'Fallback replication triggered: {}'.format(path))
                    # Workaround the PREP deadlock issue: Restrict threads to 1.
                    ofFlags = "numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(data_resc_name, to_path)
                    msi.data_obj_repl(ctx, path, ofFlags, irods_types.BytesBuf())
                    # Mark as correctly replicated
                    count_ok += 1
                except msi.Error as e:
                    log.write(ctx, 'ERROR - The file could not be replicated: {}'.format(str(e)))
                    try:
                        ctx.msi_add_avu('-d', path, errorattr, "{},{}".format(from_path, to_path), "")
                    except Exception:
                        pass

            # Remove replication_scheduled flag no matter if replication succeeded or not.
            # rods should have been given own access via policy to allow AVU changes
            avu_deleted = False
            try:
                if backwards_compatibility:
                    avu.rmw_from_data(ctx, path, attr, "{},{}".format(from_path, to_path))
                else:
                    avu.rmw_from_data(ctx, path, attr, "{},{},{}".format(from_path, to_path, balance_id))
                avu_deleted = True
            except Exception:
                avu_deleted = False

            # Try removing attr/resc meta data again with other ACL's
            if not avu_deleted:
                try:
                    # The object's ACLs may have changed.
                    # Force the ACL and try one more time.
                    msi.sudo_obj_acl_set(ctx, "", "own", user.full_name(ctx), path, "")
                    if backwards_compatibility:
                        avu.rmw_from_data(ctx, path, attr, "{},{}".format(from_path, to_path))
                    else:
                        avu.rmw_from_data(ctx, path, attr, "{},{},{}".format(from_path, to_path, balance_id))
                except Exception:
                    # error => report it but still continue
                    log.write(ctx, "ERROR - Scheduled replication of <{}>: could not remove schedule flag".format(path))

        # Total replication process completed
        log.write(ctx, "Batch replication job finished. {}/{} objects replicated successfully.".format(count_ok, count))


def is_replication_blocked_by_admin(ctx):
    """Admin can put the replication process on a hold by adding a file called 'stop_replication' in collection /yoda/flags.

    :param ctx: Combined type of a callback and rei struct

    :returns: Boolean indicating if admin put replication on hold.
    """
    zone = user.zone(ctx)
    path = "/{}/yoda/flags/stop_replication".format(zone)
    return collection.exists(ctx, path)
