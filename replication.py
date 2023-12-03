# -*- coding: utf-8 -*-
"""Functions for replication management."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

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

    # Mark data object for batch replication by setting 'org_replication_scheduled' metadata.
    try:
        # Give rods 'own' access so that they can remove the AVU.
        msi.set_acl(ctx, "default", "own", "rods#{}".format(zone), path)

        msi.add_avu(ctx, '-d', path, constants.UUORGMETADATAPREFIX + "replication_scheduled", "{},{}".format(source_resource, target_resource), "")
    except msi.Error as e:
        # iRODS error for CAT_UNKNOWN_FILE can be ignored.
        if str(e).find("-817000") == -1:
            error_status = re.search("status \[(.*?)\]", str(e))
            log.write(ctx, "Scheduled replication of data object {} failed with error {}".format(path, error_status.group(1)))
        else:
            pass


@rule.make()
def rule_replicate_batch(ctx, verbose, rss_limit='1000000000', dry_run='0'):
    """Scheduled replication batch job.

    Performs replication for all data objects marked with 'org_replication_scheduled' metadata.
    The metadata value indicates the source and destination resource.

    :param ctx:     Combined type of a callback and rei struct
    :param verbose: Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    :max_rss:       When not '0' maximum amount of rss memory in bytes before stopping, after first data object
    :param dry_run: When '1' do not actually replicate, only log what would have replicated
    """
    count         = 0
    count_ok      = 0
    print_verbose = (verbose == '1')
    no_action     = (dry_run == '1')

    attr = constants.UUORGMETADATAPREFIX + "replication_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "replication_failed"

    # Stop further execution if admin has blocked replication process.
    if is_replication_blocked_by_admin(ctx):
        log.write(ctx, "[replication] Batch replication job is stopped")
    else:
        log.write(ctx, "[replication] Batch replication job started")

        minimum_timestamp = int(time.time() - config.async_replication_delay_time)

        log.write(ctx, "[replication] verbose = {}".format(verbose))
        log.write(ctx, "[replication] async_replication_delay_time = {} seconds".format(config.async_replication_delay_time))
        log.write(ctx, "[replication] rss_limit = {} bytes".format(rss_limit))
        log.write(ctx, "[replication] dry_run = {}".format(dry_run))
        show_memory_usage(ctx)

        iter = list(genquery.Query(ctx,
                    ['ORDER(DATA_ID)', 'COLL_NAME', 'DATA_NAME', 'META_DATA_ATTR_VALUE'],
                    "META_DATA_ATTR_NAME = '{}' AND DATA_MODIFY_TIME n<= '{}'".format(attr, minimum_timestamp),
                    output=genquery.AS_LIST))

        for row in iter:
            # Stop further execution if admin has blocked replication process.
            if is_replication_blocked_by_admin(ctx):
                log.write(ctx, "[replication] Batch replication job is stopped")
                break

            # Check current memory usage and stop if it is above the limit.
            if memory_limit_exceeded(rss_limit):
                show_memory_usage(ctx)
                log.write(ctx, "[replication] Memory used is now above specified limit of {} bytes, stopping further processing".format(rss_limit))
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

            # "No action" is meant for easier memory usage debugging.
            if no_action:
                show_memory_usage(ctx)
                log.write(ctx, "[replication] Skipping batch replication (dry_run): would have replicated \"{}\" from {} to {}".format(path, from_path, to_path))
                continue

            if print_verbose:
                log.write(ctx, "[replication] Batch replication: copying {} from {} to {}".format(path, from_path, to_path))

            # Actual replication
            try:
                # Ensure first replica has checksum before replication.
                msi.data_obj_chksum(ctx, path, "replNum=0", irods_types.BytesBuf())

                # Workaround the PREP deadlock issue: Restrict threads to 1.
                ofFlags = "numThreads=1++++rescName={}++++destRescName={}++++irodsAdmin=++++verifyChksum=".format(from_path, to_path)
                msi.data_obj_repl(ctx, path, ofFlags, irods_types.BytesBuf())
                # Mark as correctly replicated
                count_ok += 1
            except msi.Error as e:
                log.write(ctx, '[replication] ERROR - The file could not be replicated: {}'.format(str(e)))
                avu.set_on_data(ctx, path, errorattr, "true")

            remove_replication_scheduled_flag(ctx=ctx, path=path, attr=attr)


        if print_verbose:
            show_memory_usage(ctx)

        # Total replication process completed
        log.write(ctx, "[replication] Batch replication job finished. {}/{} objects replicated successfully.".format(count_ok, count))


def remove_replication_scheduled_flag(ctx, path, attr):
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


def is_replication_blocked_by_admin(ctx):
    """Admin can put the replication process on a hold by adding a file called 'stop_replication' in collection /yoda/flags.

    :param ctx: Combined type of a callback and rei struct

    :returns: Boolean indicating if admin put replication on hold.
    """
    return data_object.exists(ctx, "/{}{}".format(user.zone(ctx), "/yoda/flags/stop_replication"))


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
    log.write(ctx, "[replication] current RSS usage: {} bytes".format(memory_rss_usage()))


def memory_limit_exceeded(rss_limit):
    """
    True when a limit other than 0 was specified and memory usage is currently
    above this limit. Otherwise False.
    """
    rss_limit = int(rss_limit)
    return rss_limit and memory_rss_usage() > rss_limit
