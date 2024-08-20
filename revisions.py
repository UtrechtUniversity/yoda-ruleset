# -*- coding: utf-8 -*-
"""Functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import datetime
import os
import random
import re
import time

import genquery
import irods_types
import psutil

import folder
import groups
from revision_strategies import get_revision_strategy
from revision_utils import calculate_end_of_calendar_day, get_balance_id, get_deletion_candidates, get_resc, get_revision_store_path, revision_cleanup_prefilter, revision_eligible
from util import *
from util.spool import get_spool_data, has_spool_data, put_spool_data

__all__ = ['api_revisions_restore',
           'api_revisions_search_on_filename',
           'api_revisions_list',
           'rule_revision_batch',
           'rule_revisions_cleanup_collect',
           'rule_revisions_cleanup_process',
           'rule_revisions_cleanup_scan']


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
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'

    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    qdata = genquery.Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                           "META_DATA_ATTR_NAME = '" + originalPathKey + "' "
                           "AND META_DATA_ATTR_VALUE like '/" + zone + "/home/%" + searchString + "%' "
                           "AND COLL_NAME like '" + startpath + "%' ",
                           offset=offset, limit=limit, output=genquery.AS_DICT)

    # step through results and enrich with wanted data
    for rev in list(qdata):
        rev_data = {}
        rev_data['main_revision_coll'] = rev['COLL_NAME']
        rev_data['main_original_dataname'] = pathutil.basename(rev['META_DATA_ATTR_VALUE'])
        rev_data['original_path'] = rev['META_DATA_ATTR_VALUE']
        # strip off data object name
        rev_data['collection_exists'] = collection.exists(ctx, '/'.join(rev_data['original_path'].split(os.path.sep)[:-1]))
        # strip off /zone/home/
        rev_data['original_coll_name'] = '/'.join(rev_data['original_path'].split(os.path.sep)[3:])

        iter = genquery.row_iterator(
            "DATA_ID",
            "COLL_NAME = '" + rev_data['main_revision_coll'] + "' "
            "AND META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
            "AND META_DATA_ATTR_VALUE = '" + rev_data['main_original_dataname'] + "' ",  # *originalDataName
            genquery.AS_DICT, ctx)

        for _row in iter:
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
                                "META_DATA_ATTR_NAME = '" + originalPathKey + "' "
                                "AND META_DATA_ATTR_VALUE like '/" + zone + "/home/%" + searchString + "%' "
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
    if groups.user_role(ctx, user_full_name, target_group_name) in ['none', 'reader']:
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

    if groups.user_role(ctx, user_full_name, origin_group_name) in ['none']:
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
        data_object.copy(ctx, source_path, coll_target + '/' + new_filename, True)
    except msi.Error as e:
        return api.Error('copy_failed', 'The file could not be copied', str(e))

    return api.Result.ok()


def resource_modified_post_revision(ctx, resource, zone, path):
    """Create revisions on file modifications.

    This policy should trigger whenever a new file is added or modified
    in the workspace of a Research team. This should be done asynchronously.
    Triggered from instance specific rulesets.

    :param ctx:      Combined type of a callback and rei struct
    :param resource: The resource where the original is written to
    :param zone:     Zone where the original can be found
    :param path:     Path of the original
    """
    size = data_object.size(ctx, path)
    groups = data_object.get_group_owners(ctx, path)
    if groups:
        revision_store = get_revision_store(ctx, groups[0][0])
        revision_store_exists = revision_store is not None
    else:
        revision_store_exists = False

    should_create_rev, _ = revision_eligible(constants.UUMAXREVISIONSIZE, size is not None, size, path, groups, revision_store_exists)
    if not should_create_rev:
        return

    revision_avu_name = constants.UUORGMETADATAPREFIX + "revision_scheduled"
    revision_avu_value = resource + ',' + str(random.randint(1, 64))

    # Mark data object for batch revision by setting 'org_revision_scheduled' metadata.
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
                                                      pathutil.dirname(path), pathutil.basename(path), revision_avu_name),
                                                  offset=0, limit=1, output=genquery.AS_LIST))) > 0

        if not already_has_avu:
            msi.add_avu(ctx, '-d', path, revision_avu_name, revision_avu_value, "")

    except msi.Error as e:
        if "-817000" in str(e):
            # CAT_UNKNOWN_FILE: object has been removed in the mean time. No need to create revision anymore.
            pass
        elif "-806000" in str(e):
            # CAT_SQL_ERROR: this AVU is already present. No need to set it anymore.
            pass
        else:
            error_status = re.search("status \[(.*?)\]", str(e))
            log.write(ctx, "Schedule revision of data object {} failed with error {}".format(path, error_status.group(1)))


@rule.make()
def rule_revision_batch(ctx, verbose, balance_id_min, balance_id_max, batch_size_limit, dry_run='0'):
    """Scheduled revision creation batch job.

    Creates revisions for all data objects (in research space) marked with 'org_revision_scheduled' metadata.

    For load balancing purposes each data object has been randomly assigned a number (balance_id) between 1-64.
    To enable efficient parallel batch processing, each batch job gets assigned a range of numbers. For instance 1-32.
    The corresponding job will only process data objects with a balance id within the range.

    :param ctx:              Combined type of a callback and rei struct
    :param verbose:          Whether to log verbose messages for troubleshooting ('1': yes, anything else: no)
    :param balance_id_min:   Minimum balance id for batch jobs (value 1-64)
    :param balance_id_max:   Maximum balance id for batch jobs (value 1-64)
    :param batch_size_limit: Maximum number of items to be processed within one batch
    :param dry_run:          When '1' do not actually create revisions, only log what would have been created

    :raises Exception:       If one of the parameters is invalid
    """
    count         = 0
    count_ok      = 0
    count_ignored = 0
    print_verbose = (verbose == '1')
    no_action     = (dry_run == '1')

    attr = constants.UUORGMETADATAPREFIX + "revision_scheduled"
    errorattr = constants.UUORGMETADATAPREFIX + "revision_failed"

    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "The revision creation job can only be started by a rodsadmin user.")
        return

    if not (batch_size_limit.isdigit() and int(batch_size_limit) > 0):
        raise Exception("Batch size limit is invalid. It needs to be a positive integer.")

    if not ((balance_id_min.isdigit() and int(balance_id_min) >= 1 and int(balance_id_min) <= 64)
            and (balance_id_max.isdigit() and int(balance_id_max) >= 1 and int(balance_id_max) <= 64)):
        raise Exception("Balance ID is invalid. The balance IDs need to be integers between 1 and 64.")

    # Stop further execution if admin has blocked revision process.
    if is_revision_blocked_by_admin(ctx):
        log.write(ctx, "Batch revision job is stopped")
    else:
        log.write(ctx, "Batch revision job started - balance id: {}-{}".format(balance_id_min, balance_id_max))

        minimum_timestamp = int(time.time() - config.async_revision_delay_time)

        # Get list of up to batch size limit of data objects (in research space) scheduled for revision, taking into account
        # modification time.
        log.write(ctx, "verbose = {}".format(verbose))
        if print_verbose:
            log.write(ctx, "async_revision_delay_time = {} seconds".format(config.async_revision_delay_time))
            log.write(ctx, "max_rss = {} bytes".format(config.async_revision_max_rss))
            log.write(ctx, "dry_run = {}".format(dry_run))
            show_memory_usage(ctx)

        iter = list(genquery.Query(ctx,
                    ['ORDER(DATA_ID)', 'COLL_NAME', 'DATA_NAME', 'META_DATA_ATTR_VALUE'],
                    "META_DATA_ATTR_NAME = '{}' AND COLL_NAME like '/{}/home/{}%' AND DATA_MODIFY_TIME n<= '{}'".format(
                        attr,
                        user.zone(ctx),
                        constants.IIGROUPPREFIX,
                        minimum_timestamp),
                    offset=0, limit=int(batch_size_limit), output=genquery.AS_LIST))
        for row in iter:
            # Stop further execution if admin has blocked revision process.
            if is_revision_blocked_by_admin(ctx):
                log.write(ctx, "Batch revision job is stopped")
                break

            # Check current memory usage and stop if it is above the limit.
            if memory_limit_exceeded(config.async_revision_max_rss):
                show_memory_usage(ctx)
                log.write(ctx, "Memory used is now above specified limit of {} bytes, stopping further processing".format(config.async_revision_max_rss))
                break

            # Perform scheduled revision creation for one data object.
            data_id = row[0]
            path    = row[1] + "/" + row[2]

            # Metadata value contains resc and balance id for load balancing purposes.
            resc = get_resc(row)
            balance_id = get_balance_id(row, path)

            # Check whether balance id is within the range for this job.
            if balance_id < int(balance_id_min) or balance_id > int(balance_id_max):
                # Skip this one and go to the next data object for revision creation.
                continue

            # For getting the total count, only count the data objects within the wanted range
            count += 1

            # "No action" is meant for easier memory usage debugging.
            if no_action:
                show_memory_usage(ctx)
                log.write(ctx, "Skipping creating revision (dry_run): would have created revision for {} on resc {}".format(path, resc))
                continue

            if print_verbose:
                log.write(ctx, "Batch revision: creating revision for {} on resc {}".format(path, resc))

            revision_created = check_eligible_and_create_revision(ctx, print_verbose, attr, errorattr, data_id, resc, path)
            if revision_created:
                count_ok += 1
            else:
                count_ignored += 1

        if print_verbose:
            show_memory_usage(ctx)

        # Total revision process completed
        log.write(ctx, "Batch revision job finished. {}/{} objects processed successfully. ".format(count_ok, count))
        log.write(ctx, "Batch revision job ignored {} data objects in research area, excluding data objects postponed because of delay time.".format(count_ignored))


def check_eligible_and_create_revision(ctx, print_verbose, attr, errorattr, data_id, resc, path):
    """ Check that a data object is eligible for a revision, and if so, create a revision.
        Then remove or add revision flags as appropriate.

    :param ctx:           Combined type of a callback and rei struct
    :param print_verbose: Whether to log verbose messages for troubleshooting (Boolean)
    :param attr:          revision_scheduled flag name
    :param errorattr:     revision_failed flag name
    :param data_id:       data_id of the data object
    :param resc:          Name of resource
    :param path:          Path to the data object

    :returns: Whether revision was created
    """
    revision_created = False
    size = data_object.size(ctx, path)
    groups = data_object.get_group_owners(ctx, path)
    if groups:
        revision_store = get_revision_store(ctx, groups[0][0])
        revision_store_exists = revision_store is not None
    else:
        revision_store_exists = False

    should_create_rev, revision_error_msg = revision_eligible(constants.UUMAXREVISIONSIZE, size is not None, size, path, groups, revision_store_exists)
    if should_create_rev:
        revision_created = revision_create(ctx, print_verbose, data_id, resc, groups[0][0], revision_store)
    elif not should_create_rev and len(revision_error_msg):
        log.write(ctx, revision_error_msg)

    remove_revision_scheduled_flag(ctx, print_verbose, path, attr)

    # now back to the created revision
    if revision_created:
        log.write(ctx, "Revision created for {}".format(path))
        remove_revision_error_flag(ctx, data_id, path, errorattr)
    elif should_create_rev:
        # Revision should have been created but it was not
        log.write(ctx, "ERROR - Scheduled revision creation of <{}> failed".format(path))
        avu.set_on_data(ctx, path, errorattr, "true")

    return revision_created


def remove_revision_error_flag(ctx, data_id, path, errorattr):
    """Remove revision_error flag"""
    # Revision creation OK. Remove any existing error indication attribute.
    iter2 = genquery.row_iterator(
        "DATA_NAME",
        "DATA_ID = '{}' AND META_DATA_ATTR_NAME  = '{}' AND META_DATA_ATTR_VALUE = 'true'".format(data_id, errorattr),
        genquery.AS_LIST, ctx
    )
    for _row in iter2:
        # Only try to remove it if we know for sure it exists,
        # otherwise we get useless errors in the log.
        avu.rmw_from_data(ctx, path, errorattr, "%")
        # all items removed in one go -> so break from this loop through each individual item
        break


def remove_revision_scheduled_flag(ctx, print_verbose, path, attr):
    """Remove revision_scheduled flag (no matter if it succeeded or not)."""
    # rods should have been given own access via policy to allow AVU
    # changes.
    if print_verbose:
        log.write(ctx, "Batch revision: removing AVU for {}".format(path))

    # try removing attr/resc meta data
    avu_deleted = False
    try:
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
            log.write(ctx, "ERROR - Scheduled revision creation of <{}>: could not remove schedule flag".format(path))


def is_revision_blocked_by_admin(ctx):
    """Admin can put the revision process on a hold by adding a file called 'stop_revisions' in collection /yoda/flags.

    :param ctx: Combined type of a callback and rei struct

    :returns: Boolean indicating if admin put revisions on hold.
    """
    zone = user.zone(ctx)
    path = "/{}/yoda/flags/stop_revisions".format(zone)
    return collection.exists(ctx, path)


def get_revision_store(ctx, group_name):
    """Get path to revision store for group if the path exists.

    :param ctx:        Combined type of a callback and rei struct
    :param group_name: Name of group for the revision store

    :returns: path to group's revision store if exists, else None
    """
    # All revisions are stored in a group with the same name as the research group in a system collection
    # When this collection is missing, no revisions will be created. When the group manager is used to
    # create new research groups, the revision collection will be created as well.
    revision_store = os.path.join(get_revision_store_path(user.zone(ctx)), group_name)
    revision_store_exists = collection.exists(ctx, revision_store)
    return revision_store if revision_store_exists else None


def revision_create(ctx, print_verbose, data_id, resource, group_name, revision_store):
    """Create a revision of a data object in a revision folder.

    :param ctx:            Combined type of a callback and rei struct
    :param print_verbose:  Whether to print messages for troubleshooting to log (Boolean)
    :param data_id:        data_id of the data object
    :param resource:       Name of resource
    :param group_name:     Group name
    :param revision_store: Revision store

    :returns: True / False as an indication whether a revision was successfully created
    """
    revision_created = False
    log.write(ctx, "Revision_create")

    # Retrive properties of the data object
    data_properties = data_object.get_properties(ctx, data_id, resource)

    modify_time = data_properties["DATA_MODIFY_TIME"]
    data_size = data_properties["DATA_SIZE"]
    coll_id = data_properties["COLL_ID"]
    data_owner = data_properties["DATA_OWNER_NAME"]
    basename = data_properties["DATA_NAME"]
    parent = data_properties["COLL_NAME"]

    # Skip current revision if data object is not found
    if data_size is None: #  data_size cannot be None
        log.write(ctx, "ERROR - No data object found for data_id {}, move to the next revision creation".format(data_id))
        return revision_created

    path = '{}/{}'.format(parent, basename)

    # Allow rodsadmin to create subcollections.
    msi.set_acl(ctx, "default", "admin:own", "rods#{}".format(user.zone(ctx)), revision_store)

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
            return False

    if collection.exists(ctx, rev_coll):
        # Rods may not have own access yet.
        msi.set_acl(ctx, "default", "own", "rods#{}".format(user.zone(ctx)), rev_coll)
    else:
        # Inheritance is enabled - ACLs are already good.
        # (rods and the research group both have own)
        try:
            msi.coll_create(ctx, rev_coll, '1', irods_types.BytesBuf())
        except error.UUError:
            log.write(ctx, "ERROR - Failed to create staging area at <{}>".format(rev_coll))
            return False

    rev_path = rev_coll + "/" + rev_filename

    if print_verbose:
        log.write(ctx, "Creating revision {} -> {}".format(path, rev_path))

    # Actual copying to revision store
    try:
        # Workaround the PREP deadlock issue: Restrict threads to 1.
        data_object.copy(ctx, path, rev_path, True)

        revision_created = True

        # Add original metadata to revision data object.
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_id", data_id)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_path", path)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_coll_name", parent)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_name", basename)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_data_owner_name", data_owner)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_coll_id", coll_id)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_modify_time", modify_time)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_group_name", group_name)
        avu.set_on_data(ctx, rev_path, constants.UUORGMETADATAPREFIX + "original_filesize", data_size)
    except msi.Error as e:
        log.write(ctx, 'ERROR - The file could not be copied: {}'.format(str(e)))

    return revision_created


def revision_cleanup_scan_revision_objects(ctx, revision_list):
    """Obtain information about all revisions.

    :param ctx: Combined type of a callback and rei struct
    :param revision_list: List of revision data object IDs

    :returns:   Nested list, where the outer list represents revisioned data objects,
                and the inner list represents revisions for that data object.
                Each revision is represented by a list of length three (revision ID,
                modification epoch time, revision path)
    """
    QUERY_BATCH_SIZE = 100
    ORIGINAL_PATH_ATTRIBUTE = constants.UUORGMETADATAPREFIX + 'original_path'
    ORIGINAL_MODIFY_TIME_ATTRIBUTE = constants.UUORGMETADATAPREFIX + 'original_modify_time'

    revision_store = get_revision_store_path(user.zone(ctx))

    ids = list(revision_list)
    path_dict = {}
    rev_dict = {}

    while len(ids) > 0:
        batch_ids = ids[:QUERY_BATCH_SIZE]
        batch_id_string = "({})".format(",".join(map(lambda e: "'{}'".format(e), batch_ids)))
        ids = ids[QUERY_BATCH_SIZE:]

        # first, get original_path and ids for every revision
        original_paths = genquery.row_iterator(
            "order(META_DATA_ATTR_VALUE), order_desc(DATA_ID)",
            "META_DATA_ATTR_NAME = '" + ORIGINAL_PATH_ATTRIBUTE + "'"
            " AND COLL_NAME like '" + revision_store + "/%' AND DATA_ID IN " + batch_id_string,
            genquery.AS_LIST, ctx)

        for row in original_paths:
            original_path = row[0]
            revision_id = row[1]
            if original_path in path_dict:
                path_dict[original_path].append(revision_id)
            else:
                path_dict[original_path] = [revision_id]

        # second, get id, path and modify time for every revision
        modify_times = genquery.row_iterator(
            "DATA_ID, COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE",
            "META_DATA_ATTR_NAME = '" + ORIGINAL_MODIFY_TIME_ATTRIBUTE + "'"
            " AND COLL_NAME like '" + revision_store + "/%' AND DATA_ID IN " + batch_id_string,
            genquery.AS_LIST, ctx
        )

        for row in modify_times:
            revision_id = row[0]
            path = row[1] + "/" + row[2]
            modify_time = row[3]
            rev_dict[revision_id] = [int(revision_id), int(modify_time), path]

    # collate revision info
    revisions_info = []
    for revisions in path_dict.values():
        revision_list = []
        for revision_id in revisions:
            if revision_id in rev_dict:
                revision_list.append(rev_dict[revision_id])
        revisions_info.append(revision_list)
    return revisions_info


def get_all_revision_data_ids(ctx):
    """"Returns all data IDs of revision data objects

        :param ctx:  Combined type of a callback and rei struct

        :yields: iterator of 2-tuples containing collection and data object IDs
    """
    revision_store = get_revision_store_path(user.zone(ctx))

    revision_objects = genquery.row_iterator(
        "order_desc(COLL_ID), DATA_ID",
        "META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'original_path' + "'"
        " AND COLL_NAME like '" + revision_store + "/%'",
        genquery.AS_LIST, ctx)

    for row in revision_objects:
        yield (row[0], row[1])


def _update_revision_store_acls(ctx):
    """Sets the revision store ACL to grant present rodsadmin user access

       :param ctx: Combined type of a callback and rei struct

       :raises Exception: if current user is not a rodsadmin
    """
    revision_store = get_revision_store_path(user.zone(ctx))
    if user.user_type(ctx) == 'rodsadmin':
        try:
            msi.set_acl(ctx, "recursive", "admin:own", user.full_name(ctx), revision_store)
            msi.set_acl(ctx, "recursive", "inherit", user.full_name(ctx), revision_store)
        except msi.Error as e:
            if "-809000" in str(e):
                # CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME: AVU is already present. No need to set it anymore.
                pass
            else:
                raise Exception("Cannot update revision store ACLs, an error eccured: error: {}".format(str(e)))
    else:
        raise Exception("Cannot update revision store ACLs, because present user is not rodsadmin.")


@rule.make(inputs=[0], outputs=[1])
def rule_revisions_cleanup_collect(ctx, target_batch_size):
    """Collect a list of revision data object IDs and puts them in the spool system for processing
       by the revision cleanup scan job.

       :param ctx:               Combined type of a callback and rei struct
       :param target_batch_size: Number of revisions to aim for in one batch. The real batch size can be
                                 more, because all revision objects in one collection are always in the
                                 same batch.

       :returns:                 Status

       :raises Exception:       If rule is executed by non-rodsadmin user
    """
    if user.user_type(ctx) != 'rodsadmin':
        raise Exception("The revision cleanup jobs can only be started by a rodsadmin user.")

    if has_spool_data(constants.PROC_REVISION_CLEANUP_SCAN):
        return "Existing revision cleanup scan spool data present. Not adding new revision cleanup data."

    log.write(ctx, "Starting revision cleanup collect process.")

    target_batch_size = int(target_batch_size)
    ingest_state = {
        "batch": [],
        "current_coll": None,
        "objects_for_current_coll": []
    }
    number_revisions = 0

    def ingest_new_data_id(ctx, coll_id, data_id, ingest_state, target_batch_size):
        """Read data object. Store it in ingest state as long as its collection ID is the same as
           the previous one, so that all data objects in the same collection are
           part of the same batch.

           If the new data object has a different collection ID from the previous
           ones, flush previously collected data objects to the batch buffer, and if
           needed from there to the spool queue.

           :param ctx:               combined type of a callback and rei struct
           :param coll_id:           collection ID
           :param data_id:           data object ID
           :param ingest_state:      ingest state dictionary
           :param target_batch_size: target batch size
        """
        if coll_id == ingest_state["current_coll"]:
            ingest_state["objects_for_current_coll"].append(data_id)
        else:
            if (len(ingest_state["batch"]) > 0
                    and len(ingest_state["batch"]) + len(ingest_state["objects_for_current_coll"]) >= target_batch_size):
                put_spool_data(constants.PROC_REVISION_CLEANUP_SCAN, [ingest_state["batch"]])
                ingest_state["batch"] = []

            ingest_state["batch"].extend(ingest_state["objects_for_current_coll"])
            ingest_state["objects_for_current_coll"] = [data_id]
            ingest_state["current_coll"] = coll_id

            if len(ingest_state["batch"]) >= target_batch_size:
                log.write(ctx, "Flush batch 2 " + str(ingest_state["batch"]))
                put_spool_data(constants.PROC_REVISION_CLEANUP_SCAN, [ingest_state["batch"]])
                ingest_state["batch"] = []

    for (coll_id, data_id) in get_all_revision_data_ids(ctx):
        number_revisions += 1
        ingest_new_data_id(ctx, coll_id, data_id, ingest_state, target_batch_size)

    if (len(ingest_state["batch"]) > 0
            and len(ingest_state["batch"]) + len(ingest_state["objects_for_current_coll"]) >= target_batch_size):
        put_spool_data(constants.PROC_REVISION_CLEANUP_SCAN, [ingest_state["batch"]])
        ingest_state["batch"] = []

    ingest_state["batch"].extend(ingest_state["objects_for_current_coll"])
    if len(ingest_state["batch"]) > 0:
        put_spool_data(constants.PROC_REVISION_CLEANUP_SCAN, [ingest_state["batch"]])

    log.write(ctx, "Collected {} revisions for revision cleanup scanning.".format(number_revisions))
    return "Revision data has been spooled for scanning"


@rule.make(inputs=[0, 1], outputs=[2])
def rule_revisions_cleanup_scan(ctx, revision_strategy_name, verbose_flag):
    """Collect revision data and put it in the spool system for processing by the revision cleanup
       scan jobs

       :param ctx:                    Combined type of a callback and rei struct
       :param revision_strategy_name: Select a revision strategy based on a string ('A', 'B', 'Simple'). See
                                      https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                                      for an explanation.
       :param verbose_flag:           "1" if rule needs to print additional information for troubleshooting, else "0"

       :returns:                Status

       :raises Exception:       If rule is executed by non-rodsadmin user
    """
    if user.user_type(ctx) != 'rodsadmin':
        raise Exception("The revision cleanup jobs can only be started by a rodsadmin user.")

    log.write(ctx, 'Revision cleanup scan job starting.')
    verbose = verbose_flag == "1"
    revisions_list = get_spool_data(constants.PROC_REVISION_CLEANUP_SCAN)

    if revisions_list is None:
        log.write(ctx, 'Revision cleanup scan job stopping - no more spooled revision scan data.')
        return "No more revision cleanup data"

    if verbose:
        log.write(ctx, "Number of revisions to scan: " + str(len(revisions_list)))
        log.write(ctx, "Scanning revisions: " + str(revisions_list))

    revision_data = revision_cleanup_scan_revision_objects(ctx, revisions_list)
    original_exists_dict = get_original_exists_dict(ctx, revision_data)
    prefiltered_revision_data = revision_cleanup_prefilter(ctx, revision_data, revision_strategy_name, original_exists_dict, verbose)
    output_data_size = len(prefiltered_revision_data)
    if output_data_size > 0:
        if verbose:
            log.write(ctx, "Revision cleanup job scan spooling {} objects for processing.".format(str(output_data_size)))
        put_spool_data(constants.PROC_REVISION_CLEANUP, [prefiltered_revision_data])
    else:
        if verbose:
            log.write(ctx, "Revision cleanup job scan - all data has been processed in prefilter stage. Processing not needed.")

    log.write(ctx, 'Revision cleanup scan job finished.')
    return 'Revision store cleanup scan job completed'


def get_original_exists_dict(ctx, revision_data):
    """Returns a dictionary that indicates which original data objects of revision data still exist

     :param ctx:                    Combined type of a callback and rei struct
     :param revision_data:          List of lists of revision tuples in (data_id, timestamp, revision_path) format

     :returns: dictionary, in which the keys are revision path. The values are booleans, and indicate whether
               the versioned data object of the revision still exists. If the revision data object does not
               have AVUs that refer to the versioned data object, assume it still exists.
    """
    result = dict()
    for data_object_data in revision_data:
        for (_data_id, _timestamp, revision_path) in data_object_data:

            try:
                result[revision_path] = versioned_data_object_exists(ctx, revision_path)
            except KeyError:
                # If we can't determine the original path, we assume the original data object
                # still exists, so that it is not automatically cleaned up by the revision cleanup job.
                # An error is logged by versioned_data_object_exists
                result[original_path] = True

    return result


def versioned_data_object_exists(ctx, revision_path):
    """Checks whether the version data object of a revision still exists

     :param ctx:                    Combined type of a callback and rei struct
     :param revision_path:          Logical path of revision data object

     :returns: boolean value that indicates whether the versioned data object still
               exists.

     :raises KeyError:              If revision data object does not have revision AVUs
                                    that point to versioned data object.
    """

    revision_avus = avu.of_data(ctx, revision_path)
    avu_dict = {a: v for (a, v, u) in revision_avus}

    try:
        original_path = os.path.join(avu_dict["org_original_coll_name"],
                                     avu_dict["org_original_data_name"])
        return data_object.exists(ctx, original_path)
    except KeyError:
        # If we can't determine the original path, we assume the original data object
        # still exists, so that it is not automatically cleaned up by the revision cleanup job.
        log.write(ctx, "Error: could not find original data object for revision " + revision_path
                       + " because revision does not have expected revision AVUs.")
        raise


@rule.make(inputs=[0, 1, 2], outputs=[3])
def rule_revisions_cleanup_process(ctx, revision_strategy_name, endOfCalendarDay, verbose_flag):
    """Applies the selected revision strategy to a batch of spooled revision data

    :param ctx:                    Combined type of a callback and rei struct
    :param revision_strategy_name: Select a revision strategy based on a string ('A', 'B', 'Simple'). See
                                   https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                                   for an explanation.
    :param endOfCalendarDay:       If zero, system will determine end of current day in seconds since epoch (1970-01-01 00:00 UTC)
    :param verbose_flag:           "1" if rule needs to print additional information for troubleshooting, else "0"

    :returns: String with status of cleanup

    :raises Exception:       If rule is executed by non-rodsadmin user
    """

    if user.user_type(ctx) != 'rodsadmin':
        raise Exception("The revision cleanup jobs can only be started by a rodsadmin user.")

    log.write(ctx, 'Revision cleanup job processing starting.')
    verbose = verbose_flag == "1"
    _update_revision_store_acls(ctx)
    revisions_list = get_spool_data(constants.PROC_REVISION_CLEANUP)

    if revisions_list is None:
        log.write(ctx, 'Revision cleanup processing job stopping - no more spooled revision data.')
        return "No more revision cleanup data"

    end_of_calendar_day = int(endOfCalendarDay)
    if end_of_calendar_day == 0:
        end_of_calendar_day = calculate_end_of_calendar_day()

    revision_strategy = get_revision_strategy(revision_strategy_name)

    # Statistics
    num_candidates = 0
    num_errors = 0

    for revisions in revisions_list:
        if verbose:
            log.write(ctx, 'Processing revisions {} ...'.format(str(revisions)))
        # Process the original path conform the bucket settings
        original_exists = versioned_data_object_exists(ctx, revisions[0][2]) if len(revisions) > 0 else False
        candidates = get_deletion_candidates(ctx, revision_strategy, revisions, end_of_calendar_day, original_exists, verbose)
        num_candidates += len(candidates)

        # Create lookup table for revision paths if needed
        if len(candidates) > 0:
            rev_paths = {r[0]: r[2] for r in revisions}

        if verbose:
            log.write(ctx, 'Candidates to be removed: {} ...'.format(str(candidates)))

        # Delete the revisions that were found being obsolete
        for revision_id in candidates:
            rev_path = rev_paths[revision_id]
            if verbose:
                log.write(ctx, 'Removing candidate: {} ...'.format(str(revision_id)))
            if not revision_remove(ctx, revision_id, rev_path):
                num_errors += 1

    log.write(ctx, 'Revision cleanup processing job completed - {} candidates for {} versioned data objects ({} successful / {} errors).'.format(
        str(num_candidates),
        str(len(revisions_list)),
        str(num_candidates - num_errors),
        str(num_errors)))
    return 'Revision store cleanup processing job completed'


def revision_remove(ctx, revision_id, revision_path):
    """Remove a revision from the revision store.

    Called by revision-cleanup.r cronjob.

    :param ctx:           Combined type of a callback and rei struct
    :param revision_id:   DATA_ID of the revision to remove
    :param revision_path: Path of the revision to remove

    :returns: Boolean indicating if revision was removed
    """
    revision_prefix = get_revision_store_path(user.zone(ctx), trailing_slash=True)
    if not revision_path.startswith(revision_prefix):
        log.write(ctx, "ERROR - sanity check fail when removing revision <{}>: <{}>".format(
            revision_id,
            revision_path))
        return False

    try:
        msi.data_obj_unlink(ctx, revision_path, irods_types.BytesBuf())
        return True
    except msi.Error as e:
        log.write(ctx, "ERROR - could not remove revision <{}>: <{}> ({}).".format(
            revision_id,
            revision_path,
            str(e)))
        return False

    log.write(ctx, "ERROR - Revision ID <{}> not found or permission denied.".format(revision_id))
    return False


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
