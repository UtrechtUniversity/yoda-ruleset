# -*- coding: utf-8 -*-
"""Functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time

import irods_types

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
    """Step through entire revision store and apply the chosen bucket strategy.

    :param ctx:              Combined type of a callback and rei struct
    :param bucketcase:       Multiple ways of cleaning up revisions can be chosen.
    :param endOfCalendarDay: If zero, system will determine end of current day in seconds since epoch (1970-01-01 00:00 UTC)

    :returns: String with status of cleanup
    """
    zone = user.zone(ctx)
    revision_store = '/' + zone + constants.UUREVISIONCOLLECTION

    if user.user_type(ctx) == 'rodsadmin':
        msi.set_acl(ctx, "recursive", "admin:own", user.full_name(ctx), revision_store)
        msi.set_acl(ctx, "recursive", "inherit", user.full_name(ctx), revision_store)

    end_of_calendar_day = int(endOfCalendarDay)
    if end_of_calendar_day == 0:
        end_of_calendar_day = calculate_end_of_calendar_day(ctx)

    # get definition of buckets
    buckets = revision_bucket_list(ctx, bucketcase)

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

        # Delete the revisions that were found being obsolete
        for revision_id in candidates:
            if not revision_remove(ctx, revision_id):
                return 'Something went wrong cleaning up revision store'

    return 'Successfully cleaned up the revision store'


def revision_remove(ctx, revision_id):
    """Remove a revision from the revision store.

    Called by revision-cleanup.r cronjob.

    :param ctx:         Combined type of a callback and rei struct
    :param revision_id: DATA_ID of the revision to remove

    :returns: Boolean indicating if revision was removed
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
            msi.data_obj_unlink(ctx, revision_path, irods_types.BytesBuf())
            return True
        except msi.Error as e:
            log.write(ctx, "revision_remove('" + revision_id + "'): Error when deleting.")
            return False

    log.write(ctx, "revision_remove('" + revision_id + "'): Revision ID not found or permission denied.")
    return False


def revision_bucket_list(ctx, case):
    """Returns a bucket list definition containing timebox of a bucket, max number of entries and start index.

    The first integer represents a time offset
    The second integer represents the number of revisions that can stay in the bucket
    The third integer represents the starting index when revisions need to remove. 0 is the newest, -1 the oldest
    revision after the current original (which should always be kept) , 1 the revision after that, etc.

    :param ctx:   Combined type of a callback and rei struct
    :param case:  Select a bucketlist based on a string

    :returns: List representing revision strategy
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
    """Returns list of all revisions

    Format: [dataId, timestamp of modification] in descending order where org_original_path=path

    :param ctx:   Combined type of a callback and rei struct
    :param path:  Path of original

    :returns: List of all revisions
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
    """Get the candidates for deletion based on the active strategy case

    :param ctx:                     Combined type of a callback and rei struct
    :param buckets:                 List of buckets
    :param revisions:               List of revisions
    :param initial_upper_time_bound: Initial upper time bound for first bucket

    :returns: List of candidates for deletion based on the active strategy case
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
    """Calculate the unix timestamp for the end of the current day (Same as start of next day).

    :param ctx: Combined type of a callback and rei struct

    :returns: End of calendar day - Timestamp of the end of the current day
    """
    import datetime
    # Get datetime of tomorrow.
    tomorrow = datetime.date.today() + datetime.timedelta(1)

    # Convert tomorrow to unix timestamp.
    return int(tomorrow.strftime("%s"))


@api.make()
def api_revisions_search_on_filename(ctx, searchString, offset=0, limit=10):
    """Search revisions of a file in a research folder and return list of corresponding revisions.

    :param ctx:          Combined type of a callback and rei struct
    :param searchString: String to search for as part of a file name
    :param offset:       Starting point in total resultset to start fetching
    :param limit:        Max size of the resultset to be returned

    :returns: Paginated revision search result
    """
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
                          'revision_count': value[0]})

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
    """Get list revisions of a file in a research folder.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to data object to find revisions for

    :returns: List revisions of a file in a research folder
    """
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
def api_revisions_restore(ctx, revision_id, overwrite, coll_target, new_filename):
    """Copy selected revision to target collection with given name.

    :param ctx:          Combined type of a callback and rei struct
    :param revision_id:  Data id of the revision to be restored
    :param overwrite:    Overwrite indication from front end {restore_no_overwrite, restore_overwrite, restore_next_to}
    :param coll_target:  Target collection to place the file
    :param new_filename: New file name as entered by user (in case of duplicate)

    :returns: API status
    """
    # New file name should not contain '\\' or '/'
    if '/' in new_filename or '\\' in new_filename:
        return api.Error('invalid_filename', 'It is not allowed to use slashes in a filename')

    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('not_allowed', 'It is not allowed to store file in the vault')

    # Check existence of target_coll
    if not collection.exists(ctx, coll_target):
        return api.Error('invalid_target', 'The target collection does not exist or is not accessible for you')

    user_full_name = user.full_name(ctx)

    # Target collection write access?
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You are not allowed to write in the selected collection')

    # Target_coll locked?
    if folder.is_locked(ctx, coll_target):
        return api.Error('not_allowed', 'The target collection is locked and therefore this revision cannot be written to the indicated collection')

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
        return api.Error('not_allowed', 'You are not allowed to view the information from this group {}'.format(origin_group_name))

    source_path = coll_origin + "/"  + filename_origin

    if source_path == '':
        return api.Error('invalid_revision', 'The indicated revision does not exist')

    if overwrite in ["restore_no_overwrite", "restore_next_to"]:
        if data_object.exists(ctx, coll_target + '/' + new_filename):
            return api.Error('duplicate_file', 'The file is already present at the indicated location')

    elif overwrite in ["restore_overwrite"]:
        restore_allowed = True

    else:
        return api.Error('invalid_action', 'Unknown requested action: {}'.format(overwrite))

    # Allowed to restore revision
    # Start actual restoration of the revision
    try:
        # Workaround the PREP deadlock issue: Restrict threads to 1.
        ofFlags = 'forceFlag=++++numThreads=1'
        msi.data_obj_copy(ctx, source_path, coll_target + '/' + new_filename, ofFlags, irods_types.BytesBuf())
    except msi.Error as e:
        return api.Error('copy_failed', 'The file could not be copied', str(e))

    return api.Result.ok()
