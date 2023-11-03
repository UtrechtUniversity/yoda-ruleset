# -*- coding: utf-8 -*-
"""Utility functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import datetime
import os

from revision_strategies import get_revision_strategy
from util import constants, log


def calculate_end_of_calendar_day(ctx):
    """Calculate the unix timestamp for the end of the current day (Same as start of next day).

    :param ctx: Combined type of a callback and rei struct

    :returns: End of calendar day - Timestamp of the end of the current day
    """
    # Get datetime of tomorrow.
    tomorrow = datetime.date.today() + datetime.timedelta(1)

    # Convert tomorrow to unix timestamp.
    return int(tomorrow.strftime("%s"))


def get_revision_store_path(ctx, zone, trailing_slash=False):
    """Produces the logical path of the revision store

       :param ctx: Combined type of a callback and rei struct
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
    :param revisions:                List of revisions for a particular data object. Each revision is represented by a 3-tupel
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
                                      with each revision represented as a 3-tupel (revision ID, modification time in epoch time, original
                                      path)
       :param revision_strategy_name: Select a revision strategy based on a string ('A', 'B', 'Simple'). See
                                      https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                                      for an explanation.
       :param verbose:                Whether to print verbose information for troubleshooting (boolean)

       :returns:                      List of versioned data objects, after prefiltered versioned data objects / revisions have been
                                      removed. Each versioned data object is represented as a list of revisions,
                                      with each revision represented as a 3-tupel (revision ID, modification time in epoch time, original
                                      path)
       """
    minimum_bucket_size = get_revision_strategy(revision_strategy_name).get_minimum_bucket_size()
    if verbose:
        log.write(ctx, "Removing following revisioned data objects in prefiltering for cleanup: "
                  + str([object for object in revisions_list if len(object) <= minimum_bucket_size]))
    return [object for object in revisions_list if len(object) > min(minimum_bucket_size, 1)]
