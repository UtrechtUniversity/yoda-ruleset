# -*- coding: utf-8 -*-
"""Utility functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import datetime
import hashlib
import os

from revision_strategies import get_revision_strategy
from util import constants, log, pathutil


def revision_eligible(max_size, data_obj_exists, size, path, groups, revision_store_exists):
    """Determine whether can create a revision of given data object.

    :param max_size:              Max size that file can be to create a revision (in bytes)
    :param data_obj_exists:       Whether the data object exists
    :param size:                  Size of the data object
    :param path:                  Path to the given data object (for logging)
    :param groups:                List of groups retrieved for this data object
    :param revision_store_exists: Whether revision store for this group exists

    :returns: 2-tuple containing True / False whether a revision should be created,
              and the message (if this is a error condition)
    """

    if not data_obj_exists:
        return False, "Data object <{}> was not found or path was collection".format(path)

    if len(groups) == 0:
        return False, "Cannot find owner of data object <{}>. It may have been removed. Skipping.".format(path)

    if len(groups) > 1:
        return False, "Cannot find unique owner of data object <{}>. Skipping.".format(path)

    if not revision_store_exists:
        return False, "Revision store collection does not exist for data object <{}>".format(path)

    _, zone, _, _ = pathutil.info(path)

    # A revision should not be created when the data object is too big,
    # but this is not an error condition
    if int(size) > max_size:
        return False, ""

    # Only create revisions for research space
    if not path.startswith("/{}/home/{}".format(zone, constants.IIGROUPPREFIX)):
        return False, ""

    if pathutil.basename(path) in constants.UUBLOCKLIST:
        return False, ""

    return True, ""


def calculate_end_of_calendar_day():
    """Calculate the unix timestamp for the end of the current day (Same as start of next day).

    :returns: End of calendar day - Timestamp of the end of the current day
    """
    # Get datetime of tomorrow.
    tomorrow = datetime.date.today() + datetime.timedelta(1)

    # Convert tomorrow to unix timestamp.
    return int(tomorrow.strftime("%s"))


def get_revision_store_path(zone, trailing_slash=False):
    """Produces the logical path of the revision store

       :param zone: zone name
       :param trailing_slash: Add a trailing slash (default: False)

       :returns: Logical path of revision store
    """
    if trailing_slash:
        return os.path.join("/" + zone, constants.UUREVISIONCOLLECTION.lstrip(os.path.sep), '')
    else:
        return os.path.join("/" + zone, constants.UUREVISIONCOLLECTION.lstrip(os.path.sep))


def get_deletion_candidates(ctx, revision_strategy, revisions, initial_upper_time_bound, verbose):
    """Get revision data objects for a particular versioned data object that should be deleted, as per
       a given revision strategy.

    :param ctx:                      Combined type of a callback and rei struct
    :param revision_strategy:        Revision strategy object
    :param revisions:                List of revisions for a particular data object. Each revision is represented by a 3-tuple
                                     (revision ID, modification time in epoch time, original path)
    :param initial_upper_time_bound: Initial upper time bound for first bucket
    :param verbose:                  Whether to print additional information for troubleshooting (boolean)

    :returns: List of candidates for deletion based on the specified revision strategy
    """
    buckets = revision_strategy.get_buckets()
    deletion_candidates = []

    # Set initial upper bound
    t2 = initial_upper_time_bound

    # List of bucket index with per bucket a list of its revisions within that bucket
    # [[data_ids0],[data_ids1]]
    bucket_revisions = []
    non_bucket_revisions = []
    revision_found_in_bucket = False

    # Sort revisions by bucket
    for bucket in buckets:
        t1 = t2
        t2 = t1 - bucket[0]

        revision_list = []
        for revision in revisions:
            if revision[1] <= t1 and revision[1] > t2:
                # Link the bucket and the revision together so its clear which revisions belong into which bucket
                revision_found_in_bucket = True
                revision_list.append(revision[0])  # append data-id
        # Link the collected data_ids (revision_ids) to the corresponding bucket
        bucket_revisions.append(revision_list)

    # Get revisions that predate all buckets
    for revision in revisions:
        if revision[1] < t2:
            non_bucket_revisions.append(revision[0])

    # Per bucket find the revision candidates for deletion
    bucket_counter = 0
    for rev_list in bucket_revisions:
        bucket = buckets[bucket_counter]

        max_bucket_size = bucket[1]
        bucket_start_index = bucket[2]

        if len(rev_list) > max_bucket_size:
            nr_to_be_removed = len(rev_list) - max_bucket_size

            count = 0
            if bucket_start_index >= 0:
                while count < nr_to_be_removed:
                    # Add revision to list of removal
                    index = bucket_start_index + count
                    if verbose:
                        log.write(ctx, 'Scheduling revision <{}> in bucket <{}> for removal.'.format(str(index),
                                                                                                     str(bucket)))
                    deletion_candidates.append(rev_list[index])
                    count += 1
            else:
                while count < nr_to_be_removed:
                    index = len(rev_list) + (bucket_start_index) - count
                    if verbose:
                        log.write(ctx, 'Scheduling revision <{}> in bucket <{}> for removal.'.format(str(index),
                                                                                                     str(bucket)))
                    deletion_candidates.append(rev_list[index])
                    count += 1

        bucket_counter += 1  # To keep conciding with strategy list

    # If there are revisions in any bucket, remove all revisions before defined buckets. If there are
    # no revisions in buckets, remove all revisions before defined buckets except the last one.
    if len(non_bucket_revisions) > 1 or (len(non_bucket_revisions) == 1 and revision_found_in_bucket):
        nr_to_be_removed = len(non_bucket_revisions) - (0 if revision_found_in_bucket else 1)
        count = 0
        while count < nr_to_be_removed:
            index = count + (0 if revision_found_in_bucket else 1)
            if verbose:
                log.write(ctx, 'Scheduling revision <{}> (older than buckets) for removal.'.format(str(index)))
            deletion_candidates.append(non_bucket_revisions[index])
            count += 1

    return deletion_candidates


def revision_cleanup_prefilter(ctx, revisions_list, revision_strategy_name, verbose):
    """Filters out revisioned data objects from a list if we can easily determine that they don't meet criteria for being removed,
       for example if the number of revisions is at most one, and the minimum bucket size is at least one.

       This prefilter is performed in the scan phase. A full check of the remaining versioned data objects will be performed in the
       processing phase.

       The purpose of this function is to filter out revisions that obviously don't need further processing, so as to make the cleanup
       process more efficient.

       :param ctx:                    Combined type of a callback and rei struct
       :param revisions_list:         List of versioned data objects. Each versioned data object is represented as a list of revisions,
                                      with each revision represented as a 3-tuple (revision ID, modification time in epoch time, original
                                      path)
       :param revision_strategy_name: Select a revision strategy based on a string ('A', 'B', 'Simple'). See
                                      https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                                      for an explanation.
       :param verbose:                Whether to print verbose information for troubleshooting (boolean)

       :returns:                      List of versioned data objects, after prefiltered versioned data objects / revisions have been
                                      removed. Each versioned data object is represented as a list of revisions,
                                      with each revision represented as a 3-tuple (revision ID, modification time in epoch time, original
                                      path)
       """
    minimum_bucket_size = get_revision_strategy(revision_strategy_name).get_minimum_bucket_size()
    if verbose:
        log.write(ctx, "Removing following revisioned data objects in prefiltering for cleanup: "
                  + str([object for object in revisions_list if len(object) <= minimum_bucket_size]))
    return [object for object in revisions_list if len(object) > min(minimum_bucket_size, 1)]


def get_resc(row):
    """Get the resc id for a data object given the metadata provided (for revision job).

    :param row: metadata for the data object

    :returns: resc
    """
    info = row[3].split(',')
    if len(info) == 2:
        return info[0]

    # Backwards compatibility with revision metadata created in v1.8 or earlier.
    return row[3]


def get_balance_id(row, path):
    """Get the balance id for a data object given the metadata provided (for revision job).

    :param row:  metadata for the data object
    :param path: path to the data object

    :returns: Balance id
    """
    info = row[3].split(',')
    if len(info) == 2:
        return int(info[1])

    # Backwards compatibility with revision metadata created in v1.8 or earlier.
    # Determine a balance_id for this dataobject based on its path.
    # This will determine whether this dataobject will be taken into account in this job/range or another that is running parallel
    return int(hashlib.md5(path.encode('utf-8')).hexdigest(), 16) % 64 + 1
