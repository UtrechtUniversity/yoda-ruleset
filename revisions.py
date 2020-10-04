# -*- coding: utf-8 -*-
"""Functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time

import folder
import meta_form

from util import *
from util.query import Query

__all__ = ['api_revisions_restore',
           'api_revisions_search_on_filename',
           'api_revisions_list',
           'rule_revisions_clean_up']


@rule.make(inputs=range(2), outputs=range(2, 3))
def rule_revisions_clean_up(ctx, bucketcase, endOfCalendarDay):
    """
    Step through entire revision store and apply the chosen bucket strategy
    :param bucketcase       multiple ways of cleaning up revisions can be chosen.
    :parem endOfCalendarDay if zero, system will determine end of current day in seconds since epoch (1970-01-01 00:00 UTC)
    """
    zone = user.zone(ctx)
    revision_store = '/' + zone + constants.UUREVISIONCOLLECTION

    if user.user_type(ctx) == 'rodsadmin':
        msi.set_acl(ctx, "recursive", "admin:own", user.full_name(ctx), revision_store)
        msi.set_acl(ctx, "recursive", "inherit", user.full_name(ctx), revision_store)

    end_of_calender_day = int(endOfCalendarDay)
    if end_of_calender_day == 0:
        end_of_calendar_day = calculate_end_of_calendar_day(ctx)

    # get definition of buckets
    buckets = revision_bucket_list(ctx, bucketcase)
    log.write(ctx, buckets)

    # step through entire revision store and per item apply the bucket strategy
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'original_path' + "'"
        " AND COLL_NAME like '" + revision_store + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        original_path = row[0]
        # Get all related revisions
        revisions = get_revision_list(ctx, original_path)

        # Process the original path conform the bucket settings
        candidates = get_deletion_candidates(ctx, buckets, revisions, end_of_calendar_day)
        log.write(ctx, 'DELETION CANDIDATES')
        log.write(ctx, candidates)

        # Delete the revisions that were found being obsolete
        for revision_id in candidates:
            if not revision_remove(ctx, revision_id):
                return 'Something went wrong cleaning up revision store'

    return 'Successfully cleaned up the revision store'


def revision_remove(ctx, revision_id):
    """ Remove a revision from the revision store.
    Called by revision-cleanup.r cronjob.

    :param revisionId       DATA_ID of the revision to remove
    """
    zone = user.zone(ctx)
    revision_store = '/' + zone + constants.UUREVISIONCOLLECTION

    # Check presence of specific revision in revision store
    iter = genquery.row_iterator(
        "COLL_NAME, DATA_NAME",
        "DATA_ID = '" + revision_id + "' AND COLL_NAME like '" + revision_store + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # revision is found
        try:
            revision_path = row[0] + '/' + row[1]
            # log.write(ctx,  revision_path)
            msi.data_obj_unlink(ctx, revision_path, irods_types.BytesBuf())
            log.write(ctx, "revision_remove('" + revision_id + "'): Successfully deleted " + revision_path + " from revision store.")
            return True
        except msi.Error as e:
            log.write(ctx, "revision_remove('" + revision_id + "'): Error when deleting.")
            return False

    log.write(ctx, "revision_remove('" + revision_id + "'): Revision ID not found or permission denied.")
    return False


def revision_bucket_list(ctx, case):
    """ Returns a bucket list definition containing timebox of a bucket, max number of entries and start index.
    The first integer represents a time offset
    The second integer represents the number of revisions that can stay in the bucket
    The third integer represents the starting index when revisions need to remove. 0 is the newest, -1 the oldest
    revision after the current original (which should always be kept) , 1 the revision after that, etc.

    :param case  Select a bucketlist based on a string

    """
    # Time to second conversion
    HOURS = 3600
    DAYS = 86400
    WEEKS = 604800

    if case == 'A':
        return [
            [HOURS * 6, 1, 1],
            [HOURS * 12, 1, 0],
            [HOURS * 18, 1, 0],
            [DAYS * 1, 1, 0],
            [DAYS * 2, 1, 0],
            [DAYS * 3, 1, 0],
            [DAYS * 4, 1, 0],
            [DAYS * 5, 1, 0],
            [DAYS * 6, 1, 0],
            [WEEKS * 1, 1, 0],
            [WEEKS * 2, 1, 0],
            [WEEKS * 3, 1, 0],
            [WEEKS * 4, 1, 0],
            [WEEKS * 8, 1, 0],
            [WEEKS * 12, 1, 0],
            [WEEKS * 16, 1, 0]
        ]
    elif case == 'Simple':
        return [
            [WEEKS * 16, 16, 0],
        ]
    else:
        # case B, default case
        return [
            [HOURS * 12, 2, 1],
            [DAYS * 1, 2, 1],
            [DAYS * 3, 2, 0],
            [DAYS * 5, 2, 0],
            [WEEKS * 1, 2, 1],
            [WEEKS * 3, 2, 0],
            [WEEKS * 8, 2, 0],
            [WEEKS * 16, 2, 0]
        ]


def get_revision_list(ctx, path):
    """
    Returns list of all revisions [dataId, timestamp of modification] in descending order where org_original_path=path
    :param path  path of original
    """
    candidates = []
    zone = user.zone(ctx)
    revision_store = '/' + zone + constants.UUREVISIONCOLLECTION

    iter = genquery.row_iterator(
        "DATA_ID, order_desc(DATA_ID)",
        "META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + "original_path" + "'  "
        " AND META_DATA_ATTR_VALUE = '" + path + "' "
        " AND COLL_NAME like '" + revision_store + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # Get modification time
        modify_time = 0
        iter2 = genquery.row_iterator(
            "META_DATA_ATTR_VALUE",
            "META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + "original_modify_time" + "' "
            "AND DATA_ID = '" + row[0] + "'",
            genquery.AS_LIST, ctx
        )
        for row2 in iter2:
            modify_time = int(row2[0])
        candidates.append([row[0], modify_time])

    return candidates


def get_deletion_candidates(ctx, buckets, revisions, initial_upper_time_bound):
    """ Get the candidates for deletion based on the active strategy case

    :param buckets
    :param revisions
    :param intial_upper_time_bound
    """

    deletion_candidates = []

    # Set initial upper bound
    t2 = initial_upper_time_bound

    # List of bucket index with per bucket a list of its revisions within that bucket
    # [[data_ids0],[data_ids1]]
    bucket_revisions = []

    for bucket in buckets:
        t1 = t2
        t2 = t1 - bucket[0]

        revision_list = []
        for revision in revisions:
            if revision[1] <= t1 and revision[1] > t2:
                # Link the bucket and the revision together so its clear which revisions belong into which bucket
                revision_list.append(revision[0])  # append data-id
        # Link the collected data_ids (revision_ids) to the corresponding bucket
        bucket_revisions.append(revision_list)

    log.write(ctx, '+++++ BUCKET REV LIST++++')
    log.write(ctx, bucket_revisions)

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
                    deletion_candidates.append(rev_list[bucket_start_index + count])
                    count += 1
            else:
                while count < nr_to_be_removed:
                    deletion_candidates.append(rev_list[len(rev_list) + (bucket_start_index) - count])
                    count += 1

        bucket_counter += 1  # To keep conciding with strategy list

    return deletion_candidates


def calculate_end_of_calendar_day(ctx):
    """
    Calculate the unix timestamp for the end of the current day (Same as start of next day).
    returns end of calendar day - Timestamp of the end of the current day

    """
    import datetime
    # Get datetime of tomorrow.
    tomorrow = datetime.date.today() + datetime.timedelta(1)

    # Convert tomorrow to unix timestamp.
    return int(tomorrow.strftime("%s"))


@api.make()
def api_revisions_search_on_filename(ctx, searchString, offset=0, limit=10):
    """Search revisions of a file in a research folder."""
    zone = user.zone(ctx)

    dict_org_paths = {}
    multiple_counted = 0

    # Return nothing if in fact requested ALL
    if len(searchString) == 0:
        return {'total': 0,
                'items': revisions}

    originalDataNameKey = constants.UUORGMETADATAPREFIX + 'original_data_name'
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    qdata = Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                  "META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
                  "AND META_DATA_ATTR_VALUE like '" + searchString + "%' "
                  "AND COLL_NAME like '" + startpath + "%' ",
                  offset=offset, limit=limit, output=query.AS_DICT)

    # step through results and enrich with wanted data
    for rev in list(qdata):
        rev_data = {}
        rev_data['main_revision_coll'] = rev['COLL_NAME']
        rev_data['main_original_dataname'] = rev['META_DATA_ATTR_VALUE']

        # Situations in which a data_object including its parent folder is removed.
        # And after a while gets reintroduced

        # Hier de daadwerkelijke revisies ophalen
        # Dit bepaalt het TOTAL REVISIONS
        iter = genquery.row_iterator(
            "DATA_ID",
            "COLL_NAME = '" + rev_data['main_revision_coll'] + "' "
            "AND META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
            "AND META_DATA_ATTR_VALUE = '" + rev_data['main_original_dataname'] + "' ",  # *originalDataName
            genquery.AS_DICT, ctx)

        for row in iter:
            log.write(ctx, row['DATA_ID'])

            # based on data id get original_coll_name
            iter2 = genquery.row_iterator(
                "META_DATA_ATTR_VALUE",
                "DATA_ID = '" + row['DATA_ID'] + "' "
                "AND META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'original_path' + "' ",
                genquery.AS_DICT, ctx)
            for row2 in iter2:
                rev_data['original_coll_name'] = row2['META_DATA_ATTR_VALUE']

            rev_data['collection_exists'] = collection.exists(ctx, '/'.join(rev_data['original_coll_name'].split(os.path.sep)[:-1]))
            rev_data['original_coll_name'] = '/'.join(rev_data['original_coll_name'].split(os.path.sep)[3:])

            # Data is collected on the basis of ORG_COLL_NAME, duplicates can be present
            try:
                # This is a double entry and has to be corrected in the total returned to the frontend 
                detail = dict_org_paths[rev_data['original_coll_name']]
                total = detail[0] + 1
                dict_org_paths[rev_data['original_coll_name']] = [total, detail[1], detail[2]]
                # Increment correction as the main total is based on the first query. 
                # This however can have multiple entries which require correction
                multiple_counted += 1
            except KeyError:
                # [count, collect-exists, data-name]
                dict_org_paths[rev_data['original_coll_name']] = [1, rev_data['collection_exists'], rev['META_DATA_ATTR_VALUE']]

    # create a list from collected data in dict_org_paths
    revisions = []
    for key, value in dict_org_paths.items():
        revisions.append({'main_original_dataname': value[2],
                          'collection_exists': value[1],
                          'original_coll_name': key,
                          'revision_count': value[0]
                         })

    # Alas an extra Query is required to get the total number of rows
    qtotalrows = Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                       "META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
                       "AND META_DATA_ATTR_VALUE like '" + searchString + "%' "
                       "AND COLL_NAME like '" + startpath + "%' ",
                       offset=0, limit=None, output=query.AS_DICT)

    # qtotalrows.total_rows() moet worden verminderd met het aantal ontdubbelde entries
    return {'total': qtotalrows.total_rows() - multiple_counted,
            'items': revisions}


@api.make()
def api_revisions_list(ctx, path):
    """List revisions of a files in a research folder."""
    originalPathKey = ''
    startpath = ''

    zone = user.zone(ctx)

    revisions = []
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    iter = genquery.row_iterator(
        "DATA_ID, COLL_NAME, order(DATA_NAME)",
        "META_DATA_ATTR_NAME = '" + originalPathKey + "' "
        "AND META_DATA_ATTR_VALUE = '" + path + "' "
        "AND COLL_NAME like '" + startpath + "%' ",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        revisionPath = row[1] + '/' + row[2]

        iter2 = genquery.row_iterator(
            "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE ",
            "DATA_ID = '" + row[0] + "' ",
            genquery.AS_LIST, ctx
        )

        meta_data = {"data_id": row[0]}
        for row2 in iter2:
            meta_data[row2[0]] = row2[1]

        meta_data["dezoned_coll_name"] = '/' + '/'.join(meta_data["org_original_coll_name"].split(os.path.sep)[3:])

        meta_data["org_original_modify_time"] = time.strftime('%Y/%m/%d %H:%M:%S',
                                                              time.localtime(int(meta_data["org_original_modify_time"])))

        revisions.append(meta_data)

    return {"revisions": revisions}


@api.make()
# "restore_no_overwrite"
# "restore_overwrite" -> overwrite the file
# "restore_next_to" -> revision is places next to the file it conflicted with by adding
#
# {restore_no_overwrite, restore_overwrite, restore_next_to}
#   With "restore_no_overwrite" the front end tries to copy the selected revision in *target
#    If the file already exist the user needs to decide what to do.
#     Function exits with corresponding status so front end can take action
def api_revisions_restore(ctx, revision_id, overwrite, coll_target, new_filename):
    """Copy selected revision to target collection with given name."""
    # New file name should not contain '\\' or '/'
    if '/' in new_filename or '\\' in new_filename:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in a filename"}

    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to store file in the vault"}

    # Check existence of target_coll
    if not collection.exists(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The target collection does not exist or is not accessible for you"}

    user_full_name = user.full_name(ctx)

    # Target collection write access?
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You are not allowed to write in the selected collection"}

    # Target_coll locked?
    if folder.is_locked(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The target collection is locked and therefore this revision cannot be written to the indicated collection"}

    # Read access in org collection?
    # Find actual revision inf on revision_id
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    original_path   = ''
    source_path     = ''
    coll_origin     = ''
    filename_origin = ''
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME, META_DATA_ATTR_VALUE",
        "DATA_ID = '" + revision_id + "' "
        " AND META_DATA_ATTR_NAME = '" + originalPathKey + "' ",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        coll_origin = row[1]
        filename_origin = row[0]
        original_path = row[2]

    origin_group_name = original_path.split('/')[3]

    if meta_form.user_member_type(ctx, origin_group_name, user_full_name) in ['none']:
        return {"proc_status": "nok",
                "proc_status_info": "You are not allowed to view the information from this group " + origin_group_name}

    source_path = coll_origin + "/"  + filename_origin

    if source_path == '':
        return {"proc_status": "nok",
                "proc_status_info": "The indicated revision does not exist"}

    if overwrite in ["restore_no_overwrite", "restore_next_to"]:
        if data_object.exists(ctx, coll_target + '/' + new_filename):
            return {"proc_status": "ok_duplicate",
                    "proc_status_info": "The file is already present at the indicated location"}

    elif overwrite in ["restore_overwrite"]:
        restore_allowed = True

    else:
        return {"proc_status": "nok",
                "proc_status_info": "Unknown requested action: " + overwrite}

    # Allowed to restore revision
    # Start actual restoration of the revision
    try:
        # Workaround the PREP deadlock issue: Restrict threads to 1.
        ofFlags = 'forceFlag=++++numThreads=1'
        msi.data_obj_copy(ctx, source_path, coll_target + '/' + new_filename, ofFlags, irods_types.BytesBuf())
    except msi.Error as e:
        raise api.Error('copy_failed', 'The file could not be copied', str(e))

    return {"proc_status": "ok"}
