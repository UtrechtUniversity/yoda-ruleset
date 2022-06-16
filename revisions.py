# -*- coding: utf-8 -*-
"""Functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import datetime
import os
import time

import genquery
import irods_types

import folder
import meta_form
from util import *

__all__ = ['api_revisions_restore',
           'api_revisions_search_on_filename',
           'api_revisions_list',
           'rule_revision_batch',
           'rule_revisions_clean_up']


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

    revisions = []
    dict_org_paths = {}
    multiple_counted = 0

    # Return nothing if search string is empty.
    if len(searchString) == 0:
        return {'total': 0,
                'items': revisions}

    originalDataNameKey = constants.UUORGMETADATAPREFIX + 'original_data_name'
    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    qdata = genquery.Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                           "META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
                           "AND META_DATA_ATTR_VALUE like '" + searchString + "%' "
                           "AND COLL_NAME like '" + startpath + "%' ",
                           offset=offset, limit=limit, output=genquery.AS_DICT)

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

    # Create a list from collected data in dict_org_paths.
    for key, value in dict_org_paths.items():
        revisions.append({'main_original_dataname': value[2],
                          'collection_exists': value[1],
                          'original_coll_name': key,
                          'revision_count': value[0]})

    # Alas an extra genquery.Query is required to get the total number of rows
    qtotalrows = genquery.Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                                "META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
                                "AND META_DATA_ATTR_VALUE like '" + searchString + "%' "
                                "AND COLL_NAME like '" + startpath + "%' ",
                                offset=0, limit=None, output=genquery.AS_DICT)

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
        pass

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


def resource_modified_post_revision(ctx, resource, zone, path):
    """Create revisions on file modifications.

    This policy should trigger whenever a new file is added or modified
    in the workspace of a Research team. This should be done asynchronously.
    Triggered from instance specific rulesets.

    :param ctx:           Combined type of a callback and rei struct
    :param resource:       The resource where the original is written to
    :param zone:           Zone where the original can be found
    :param path:           path of the original
    """
    # Only create revisions for research space
    if path.startswith("/{}/home/{}".format(zone, constants.IIGROUPPREFIX)):
        if not pathutil.basename(path) in constants.UUBLOCKLIST:
            # now create revision asynchronously by adding indication org_revision_scheduled
            msi.set_acl(ctx, "default", "own", "rods#{}".format(zone), path)
            avu.set_on_data(ctx, path, constants.UUORGMETADATAPREFIX + "revision_scheduled", resource)


# @rule.make(inputs=range(4))
@rule.make()
def rule_revision_batch(ctx, verbose, data_id, max_batch_size, delay):
    """Scheduled revision creation batch job.

    Creates revisions for all data objects marked with 'org_revision_scheduled' metadata.

    :param ctx:            Combined type of a callback and rei struct
    :param verbose:        Whether to log verbose messages for troubleshooting ('True': yes, anything else: no)
    :param data_id:        The start id to be searching from for new data objects
    :param max_batch_size: Max amount of accumulated data sizes to be handled in one batch
    :param delay:          The delay time before a new batch job is kicked off

    :returns: String with status of the batch process
    """
    log.write(ctx, '[revisions] Batch revision job is started')
    log.write(ctx, 'HDR 1')
    log.write(ctx, verbose)
    log.write(ctx, data_id)
    log.write(ctx, max_batch_size)
    log.write(ctx, delay)

    zone = user.zone(ctx)

    # Stop scheduled revision if stop flag is set. This could happen during batch processing
    if is_revision_blocked_by_admin(ctx, zone):
        log.write(ctx, "[revisions] Batch revision job is stopped due to admin interference")
        return "Batch for revision creation has been stopped"

    bucket        = 0 # holds the accumulated values of the individual datasizes
    count         = 0
    count_ok      = 0
    count_ignored = 0
    print_verbose = (verbose == 1)

    attr = constants.UUORGMETADATAPREFIX + "revision_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "revision_failed"

    # get list of data objects scheduled for revision
    iter = genquery.row_iterator(
        "ORDER(DATA_ID), COLL_NAME, DATA_NAME, DATA_SIZE, META_DATA_ATTR_VALUE",
        "META_DATA_ATTR_NAME = '{}' AND DATA_ID >='{}'".format(attr, int(data_id)),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        count += 1

        # Stop scheduled revision if stop flag is set. This could happen during batch processing
        if is_revision_blocked_by_admin(ctx, zone):
            log.write(ctx, "[revisons] Batch revision job is stopped due to admin interference")
            return "Batch for revision creation has been stopped"

        # Perform scheduled revision creation for one data object.
        path = row[1] + "/" + row[2]
        resc = row[4]
        size = int(row[3])

        if print_verbose:
            log.write(ctx, "[revisions] Batch revision: creating revision for {} on resc {}".format(path, resc))

        id = revision_create(ctx, resc, path, constants.UUMAXREVISIONSIZE, verbose)

        # Remove revision_scheduled flag no matter if it succeeded or not.
        # rods should have been given own access via policy to allow AVU
        # changes.
        if print_verbose:
            log.write(ctx, "[revisions] Batch revision: removing AVU for {}".format(path))

        # try removing attr/resc meta data
        avu_deleted = False
        try:
            # avu.rm_from_data(ctx, path, attr, resc)
            avu.rmw_from_data(ctx, path, attr, "%")  # use wildcard cause rm_from_data causes problems
            avu_deleted = True
        except Exception:
            avu_deleted = False

        # try removing attr/resc meta data again with other ACL's
        if not avu_deleted:
            try:
                # The object's ACLs may have changed.
                # Force the ACL and try one more time.
                msi.sudo_obj_acl_set(ctx, "", "own", user.full_name(ctx), path, "")
                avu.rmw_from_data(ctx, path, attr, "%")  # use wildcard cause rm_from_data causes problems
            except Exception:
                log.write(ctx, "[revisions] ERROR - Scheduled revision creation of <{}>: could not remove schedule flag".format(path))

        # now back to the created revision
        if id:
            log.write(ctx, "[revisions] Revision created for {} ID={}".format(path, id))
            count_ok += 1
            # Revision creation OK. Remove any existing error indication attribute.
            iter2 = genquery.row_iterator(
                "DATA_NAME",
                "COLL_NAME = '" + row[1] + "' AND DATA_NAME = '" + row[2] + "'"
                " AND META_DATA_ATTR_NAME  = '" + errorattr + "' AND META_DATA_ATTR_VALUE = 'true'",
                genquery.AS_LIST, ctx
            )
            for row2 in iter2:
                # Only try to remove it if we know for sure it exists,
                # otherwise we get useless errors in the log.
                avu.rmw_from_data(ctx, path, errorattr, "%")
                # all items removed in one go -> so break from this loop through each individual item
                break
        else:
            count_ignored += 1
            log.write(ctx, "[revisions] ERROR - Scheduled revision creation of <{}> failed".format(path))
            avu.set_on_data(ctx, path, errorattr, "true")

        # Determine new bucket size
        bucket += size

        # max_batch_size exceeded -> then stop current batch and kickoff the next one through a delayed rule
        if bucket >= int(max_batch_size):
            # Kickoff the next batch
            log.write(ctx, "[revisions] Batch revision job partly finished. {}/{} objects succesfully processed. {} ignored.".format(count_ok, count, count_ignored))

            # Set off the next batch from correct starting point
            next_data_id = int(row[0]) + 1
            log.write(ctx, "NEW ID: {}".format(next_data_id))
            # ?? Dit moet nog de PYTHON variant worden
            ctx.delayExec(
                "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % int(delay),
                "rule_revision_batch('%s', '%d', '%d', '%d')" % (verbose, next_data_id, int(max_batch_size), int(delay)),
                "")
            # break out of the iteration as max_batch_size has been exceeded
            log.write(ctx, '[revisions] New batch initiated')
            return '[revisions] New batch initiated'

    # Total revision process completed
    log.write(ctx, "[revisions] Batch revision job finished. {}/{} objects succesfully processed. {} ignored.".format(count_ok, count, count_ignored))


def is_revision_blocked_by_admin(ctx, zone):
    """ Admin can put the revision process on a hold by adding a file called 'stop_revisions' in collection /yoda/flags """
    iter = genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME = '" + "/{}/yoda/flags".format(zone) + "' AND DATA_NAME = 'stop_revisions'",
        genquery.AS_LIST, ctx
    )
    return (len(list(iter))>0)


def revision_create(ctx, resource, path, max_size, verbose):
    """Create a revision of a dataobject in a revision folder.

    :param ctx:      Combined type of a callback and rei struct
    :param resource: Resource to retrieve original from
    :param path:     Path of data object to create a revision for
    :param max_size: Max size of files in bytes
    :param verbose:	 Whether to print messages for troubleshooting to log (1: yes, 0: no)

    :returns: Data object ID of created revision
    """
    revision_id = ""
    print_verbose = verbose
    parent, basename = pathutil.chop(path)
    found = False

    iter = genquery.row_iterator(
        "DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID, DATA_RESC_HIER",
        "DATA_NAME = '{}' AND COLL_NAME = '{}' AND DATA_RESC_HIER like '{}%'".format(basename, parent, resource),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        data_id = row[0]
        modify_time = row[1]
        data_size = row[3]
        coll_id = row[4]
        data_owner = row[2]
        found = True
        break

    if not found:
        log.write(ctx, "[revisons] Data object <{}> was not found or path was collection".format(path))
        return ""

    if int(data_size) > max_size:
        log.write(ctx, "[revisons] Files larger than {} bytes cannot store revisions".format(max_size))
        return ""

    iter = genquery.row_iterator(
        "USER_NAME, USER_ZONE",
        "DATA_ID = '" + data_id + "' AND USER_TYPE = 'rodsgroup' AND DATA_ACCESS_NAME = 'own'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        group_name = row[0]
        user_zone = row[1]

    # All revisions are stored in a group with the same name as the research group in a system collection
    # When this collection is missing, no revisions will be created. When the group manager is used to
    # create new research groups, the revision collection will be created as well.
    revision_store = "/" + user_zone + constants.UUREVISIONCOLLECTION + "/" + group_name
    revision_store_exists = False

    iter = genquery.row_iterator(
        "COLL_ID",
        "COLL_NAME = '" + revision_store + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        revision_store_exists = True

    if revision_store_exists:
        # Allow rodsadmin to create subcollections.
        msi.set_acl(ctx, "default", "own", "rods#{}".format(user.zone(ctx)), revision_store)

        # generate a timestamp in iso8601 format to append to the filename of the revised file.
        # 2019-09-07T15:50-04:00
        iso8601 = datetime.datetime.now().replace(microsecond=0).isoformat()

        rev_filename = basename + "_" + iso8601 + data_owner
        rev_coll = revision_store + "/" + coll_id

        read_access = msi.check_access(ctx, path, 'read object', irods_types.BytesBuf())['arguments'][2]
        if read_access != b'\x01':
            try:
                msi.set_acl(ctx, "default", "read", "rods#{}".format(user.zone(ctx)), path)
            except msi.Error:
                return ""

        if collection.exists(ctx, rev_coll):
            # Rods may not have own access yet.
            msi.set_acl(ctx, "default", "own", "rods#{}".format(user.zone(ctx)), rev_coll)
        else:
            # Inheritance is enabled - ACLs are already good.
            # (rods and the research group both have own)
            try:
                msi.coll_create(ctx, rev_coll, '1', irods_types.BytesBuf())
            except error.UUError:
                log.write(ctx, "[revisons] ERROR - Failed to create staging area at <{}>".format(rev_coll))
                return ""

        rev_path = rev_coll + "/" + rev_filename

        if print_verbose:
            log.write(ctx, "[revisons] Creating revision {} -> {}".format(path, rev_path))

        # actual copying to revision store
        try:
            # Workaround the PREP deadlock issue: Restrict threads to 1.
            ofFlags = 'forceFlag=++++numThreads=1'
            msi.data_obj_copy(ctx, path, rev_path, ofFlags, irods_types.BytesBuf())

            iter = genquery.row_iterator(
                "DATA_ID",
                "COLL_NAME = '" + rev_coll + "' AND DATA_NAME = '" + rev_filename + "'",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                revision_id = row[0]

            # Add original metadata to revision data object.
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_path", path)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_coll_name", parent)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_name", basename)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_owner_name", data_owner)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_id", data_id)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_coll_id", coll_id)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_modify_time", modify_time)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_group_name", group_name)
            avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_filesize", data_size)
        except msi.Error as e:
            log.write(ctx, '[revisons] ERROR - The file could not be copied: {}'.format(str(e)))
            return ''

    return revision_id


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
        except msi.Error:
            log.write(ctx, "[revisons] ERROR - Something went wrong deleting revision <{}>: <{}>.".format(revision_id, revision_path))
            return False

    log.write(ctx, "[revisons] ERROR - Revision ID <{}> not found or permission denied.".format(revision_id))
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

    :param ctx:                      Combined type of a callback and rei struct
    :param buckets:                  List of buckets
    :param revisions:                List of revisions
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
