# -*- coding: utf-8 -*-
"""Functions for replication management."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import random
import re
import time

import genquery
import irods_types
import psutil

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
    replication_avu_name = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    replication_avu_value = "{},{},{}".format(source_resource, target_resource, random.randint(1, 64))

    # Mark data object for batch replication by setting 'org_replication_scheduled' metadata.
    try:
        # Give rods 'own' access so that they can remove the AVU.
        msi.set_acl(ctx, "default", "own", "rods#{}".format(zone), path)

        # Check whether the object already has an AVU. If we try to add the AVU when it already
        # exists, we will catch the exception below, however the SQL error would still result in log
        # clutter. Checking beforehand reduces the log clutter, though such errors can still occur
        # if an AVU is added after this check.
        already_has_avu = len(list(genquery.Query(ctx,
                                                  ['DATA_ID'],
                                                  "COLL_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = '{}'".format(
                                                      pathutil.dirname(path), pathutil.basename(path), replication_avu_name),
                                                  offset=0, limit=1, output=genquery.AS_LIST))) > 0

        if not already_has_avu:
            # Can't use mod_avu/set here (instead of add_avu) because it would be blocked by metadata policies.
            add_operation = {
                "entity_name": path,
                "entity_type": "data_object",
                "operations": [
                    {
                        "operation": "add",
                        "attribute": replication_avu_name,
                        "value": replication_avu_value,
                        "units": ""
                    }
                ]
            }
            avu.apply_atomic_operations(ctx, add_operation)
    except msi.Error as e:
        if "-817000" in str(e):
            # CAT_UNKNOWN_FILE: object has been removed in the mean time. No need to replicate it anymore.
            pass
        elif "-806000" in str(e):
            # CAT_SQL_ERROR: this AVU is already present. No need to set it anymore.
            pass
        else:
            error_status = re.search("status \[(.*?)\]", str(e))
            log.write(ctx, "Schedule replication of data object {} failed with error {}".format(path, error_status.group(1)))


@rule.make()
def rule_replicate_batch(ctx, verbose, balance_id_min, balance_id_max, batch_size_limit, dry_run):
    """Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.

    For load balancing purposes each data object has been randomly assigned a number (balance_id) between 1-64.
    To enable efficient parallel batch processing, each batch job gets assigned a range of numbers. For instance 1-32.
    The corresponding job will only process data objects with a balance id within the range.

    :param ctx:              Combined type of a callback and rei struct
    :param verbose:          Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    :param balance_id_min:   Minimum balance id for batch jobs (value 1-64)
    :param balance_id_max:   Maximum balance id for batch jobs (value 1-64)
    :param batch_size_limit: Maximum number of items to be processed within one batch
    :param dry_run:          When '1' do not actually replicate, only log what would have replicated

    """
    count         = 0
    count_ok      = 0
    print_verbose = (verbose == '1')
    no_action     = (dry_run == '1')

    attr = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "replication_failed"

    # Stop further execution if admin has blocked replication process.
    if is_replication_blocked_by_admin(ctx):
        log.write(ctx, "Batch replication job is stopped")
    else:
        log.write(ctx, "Batch replication job started - balance id: {}-{}".format(balance_id_min, balance_id_max))

        minimum_timestamp = int(time.time() - config.async_replication_delay_time)

        log.write(ctx, "verbose = {}".format(verbose))
        if print_verbose:
            log.write(ctx, "async_replication_delay_time = {} seconds".format(config.async_replication_delay_time))
            log.write(ctx, "max_rss = {} bytes".format(config.async_replication_max_rss))
            log.write(ctx, "dry_run = {}".format(dry_run))
            show_memory_usage(ctx)

        # Get list of up to batch size limit of data objects scheduled for replication, taking into account their modification time.
        iter = list(genquery.Query(ctx,
                    ['ORDER(DATA_ID)', 'COLL_NAME', 'DATA_NAME', 'META_DATA_ATTR_VALUE', 'DATA_RESC_NAME'],
                    "META_DATA_ATTR_NAME = '{}' AND DATA_MODIFY_TIME n<= '{}'".format(attr, minimum_timestamp),
                    offset=0, limit=int(batch_size_limit), output=genquery.AS_LIST))
        for row in iter:
            # Stop further execution if admin has blocked replication process.
            if is_replication_blocked_by_admin(ctx):
                log.write(ctx, "Batch replication job is stopped")
                break

            # Check current memory usage and stop if it is above the limit.
            if memory_limit_exceeded(config.async_replication_max_rss):
                show_memory_usage(ctx)
                log.write(ctx, "Memory used is now above specified limit of {} bytes, stopping further processing".format(config.async_replication_max_rss))
                break

            count += 1
            path = row[1] + "/" + row[2]

            # Metadata value contains from_path, to_path and balance id for load balancing purposes.
            info = row[3].split(',')
            from_path = info[0]
            to_path = info[1]

            if len(info) == 3:
                balance_id = int(info[2])
            else:
                # Not replicable.
                log.write(ctx, "ERROR - Invalid replication data for {}".format(path))
                try:
                    add_operation = {
                        "entity_name": path,
                        "entity_type": "data_object",
                        "operations": [
                            {
                                "operation": "add",
                                "attribute": errorattr,
                                "value": "Invalid,Invalid",
                                "units": ""
                            }
                        ]
                    }
                    avu.apply_atomic_operations(ctx, add_operation)
                except Exception:
                    pass

                # Go to next record and skip further processing.
                continue

            # Check whether balance id is within the range for this job
            if balance_id < int(balance_id_min) or balance_id > int(balance_id_max):
                # Skip this one and go to the next data object to be replicated.
                continue

            # For totalization only count the data objects that are within the specified balancing range
            count += 1
            data_resc_name = row[4]

            # "No action" is meant for easier memory usage debugging.
            if no_action:
                show_memory_usage(ctx)
                log.write(ctx, "Skipping batch replication (dry_run): would have replicated \"{}\" from {} to {}".format(path, from_path, to_path))
                continue

            if print_verbose:
                log.write(ctx, "Batch replication: copying {} from {} to {}".format(path, from_path, to_path))

            # Actual replication
            try:
                # Ensure first replica has checksum before replication.
                msi.data_obj_chksum(ctx, path, "irodsAdmin=", irods_types.BytesBuf())

                # Workaround the PREP deadlock issue: Restrict threads to 1.
                ofFlags = "numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(from_path, to_path)
                msi.data_obj_repl(ctx, path, ofFlags, irods_types.BytesBuf())
                # Mark as correctly replicated
                count_ok += 1
            except msi.Error as e:
                log.write(ctx, 'ERROR - The file {} could not be replicated from {} to {}: {}'.format(file, from_path, to_path, str(e)))

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
                        add_operation = {
                            "entity_name": path,
                            "entity_type": "data_object",
                            "operations": [
                                {
                                    "operation": "add",
                                    "attribute": errorattr,
                                    "value": "{},{}".format(from_path, to_path),
                                    "units": ""
                                }
                            ]
                        }
                        avu.apply_atomic_operations(ctx, add_operation)
                    except Exception:
                        pass

            # Remove replication_scheduled flag no matter if replication succeeded or not.
            # rods should have been given own access via policy to allow AVU changes
            avu_deleted = False
            try:
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
                    avu.rmw_from_data(ctx, path, attr, "{},{},{}".format(from_path, to_path, balance_id))
                except Exception:
                    # error => report it but still continue
                    log.write(ctx, "ERROR - Scheduled replication of <{}>: could not remove schedule flag".format(path))

        if print_verbose:
            show_memory_usage(ctx)

        # Total replication process completed
        log.write(ctx, "Batch replication job finished. {}/{} objects replicated successfully.".format(count_ok, count))


def is_replication_blocked_by_admin(ctx):
    """Admin can put the replication process on hold by adding a file called 'stop_replication' in collection /yoda/flags.

    :param ctx: Combined type of a callback and rei struct

    :returns: Boolean indicating if admin put replication on hold.
    """
    zone = user.zone(ctx)
    path = "/{}/yoda/flags/stop_replication".format(zone)
    return collection.exists(ctx, path)


def memory_rss_usage():
    """
    The RSS (resident) memory size in bytes for the current process.
    """
    p = psutil.Process()
    return p.memory_info().rss


def show_memory_usage(ctx):
    """
    For debug purposes show the current RSS usage.
    """
    log.write(ctx, "current RSS usage: {} bytes".format(memory_rss_usage()))


def memory_limit_exceeded(rss_limit):
    """
    True when a limit other than 0 was specified and memory usage is currently
    above this limit. Otherwise False.

    :param rss_limit: Max memory usage in bytes

    :returns: Boolean indicating if memory limited exceeded
    """
    rss_limit = int(rss_limit)
    return rss_limit and memory_rss_usage() > rss_limit
