# -*- coding: utf-8 -*-
"""Functions for intake module."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import fnmatch
import time

import genquery

import intake_dataset
import intake_lock
import intake_scan
from util import *


__all__ = ['api_intake_list_studies',
           'api_intake_list_dm_studies',
           'api_intake_count_total_files',
           'api_intake_list_unrecognized_files',
           'api_intake_list_datasets',
           'api_intake_scan_for_datasets',
           'api_intake_lock_dataset',
           'api_intake_unlock_dataset',
           'api_intake_dataset_get_details',
           'api_intake_dataset_add_comment',
           'api_intake_report_vault_dataset_counts_per_study',
           'api_intake_report_vault_aggregated_info',
           'api_intake_report_export_study_data',
           'rule_intake_scan_for_datasets']

INTAKE_FILE_EXCLUSION_PATTERNS = ['*.abc', '*.PNG']
""" List of file patterns not to take into account within INTAKE module."""


@api.make()
def api_intake_list_studies(ctx):
    """Get list of all studies current user is involved in.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of studies

    """
    groups = []
    user_name = user.name(ctx)
    user_zone = user.zone(ctx)

    iter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_NAME = '" + user_name + "' AND USER_ZONE = '" + user_zone + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if row[0].startswith('grp-intake-'):
            groups.append(row[0][11:])

    groups.sort()
    return groups


@api.make()
def api_intake_list_dm_studies(ctx):
    """Return list of studies current user is datamanager of.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of dm studies
    """
    datamanager_groups = []
    user_name = user.name(ctx)
    user_zone = user.zone(ctx)

    iter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_NAME = '" + user_name + "' AND USER_ZONE = '" + user_zone + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if row[0].startswith('grp-intake-'):
            study = row[0][11:]
            # Is a member of this study ... check whether member of corresponding datamanager group
            iter2 = genquery.row_iterator(
                "USER_NAME",
                "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-" + study + "'",
                genquery.AS_LIST, ctx
            )
            for row2 in iter2:
                datamanager_group = row2[0]
                if user.is_member_of(ctx, datamanager_group):
                    datamanager_groups.append(study)

    return datamanager_groups


@api.make()
def api_intake_count_total_files(ctx, coll):
    """Get the total count of all files in collection
    .
    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection from which to count all datasets

    :returns: Total file count
    """
    # Include coll name as equal names do occur and genquery delivers distinct results.
    iter = genquery.row_iterator(
        "COLL_NAME, DATA_NAME",
        "COLL_NAME like '" + coll + "%'",
        genquery.AS_LIST, ctx
    )

    count = 0
    for row in iter:
        exclusion_matched = any(fnmatch.fnmatch(row[1], p) for p in INTAKE_FILE_EXCLUSION_PATTERNS)
        if not exclusion_matched:
            count += 1

    return count


@api.make()
def api_intake_list_unrecognized_files(ctx, coll):
    """Get list of all unrecognized files for given path including relevant metadata.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection from which to list all unrecognized files
    :returns: List of unrecognized files
    """
    # check permissions
    parts = coll.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if user.is_member_of(ctx, group):
        log.write(ctx, "IS GROUP MEMBER")
    elif user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "IS DM")
    else:
        log.write(ctx, "NO PERMISSION")
        return {}

    # Include coll name as equal names do occur and genquery delivers distinct results.
    iter = genquery.row_iterator(
        "COLL_NAME, DATA_NAME, COLL_CREATE_TIME, DATA_OWNER_NAME",
        "COLL_NAME like '" + coll + "%' AND META_DATA_ATTR_NAME = 'unrecognized'",
        genquery.AS_LIST, ctx
    )

    files = []
    for row in iter:
        # Check whether object type is within exclusion pattern
        exclusion_matched = any(fnmatch.fnmatch(row[1], p) for p in INTAKE_FILE_EXCLUSION_PATTERNS)
        if not exclusion_matched:
            # Error is hardcoded! (like in the original) and initialize attributes already as empty strings.
            file_data = {"name": row[1],
                         "path": row[0],
                         "date": time.strftime('%Y-%m-%d', time.localtime(int(row[2]))),
                         "creator": row[3],
                         "error": 'Experiment type, wave or pseudocode is missing from path',
                         "experiment_type": '',
                         "pseudocode": '',
                         "wave": '',
                         "version": ''}

            # per data object get relevent metadata (experiment type, version, wave, pseudocode) if present
            iter2 = genquery.row_iterator(
                "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
                "COLL_NAME = '" + row[0] + "' AND DATA_NAME = '" + row[1] + "' AND META_DATA_ATTR_NAME in ('experiment_type', 'pseudocode', 'wave', 'version')",
                genquery.AS_LIST, ctx
            )
            for row2 in iter2:
                file_data[row2[0]] = row2[1]

            files.append(file_data)

    return files


@api.make()
def api_intake_list_datasets(ctx, coll):
    """Get list of datasets for given path.

    A dataset is distinguished by attribute name 'dataset_toplevel' which can either reside on a collection or a data object.
    That is why 2 seperate queries have to be performed.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection from which to list all datasets

    :returns: list of datasets
    """
    datasets = []

    # 1) Query for datasets distinguished by collections
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE, COLL_NAME",
        "COLL_NAME like '" + coll + "%' AND META_COLL_ATTR_NAME = 'dataset_toplevel' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dataset = get_dataset_details(ctx, row[0], row[1])
        datasets.append(dataset)

    # 2) Query for datasets distinguished dataobjects
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE, COLL_NAME",
        "COLL_NAME like '" + coll + "%' AND META_DATA_ATTR_NAME = 'dataset_toplevel' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dataset = get_dataset_details(ctx, row[0], row[1])
        datasets.append(dataset)

    return datasets


def get_dataset_details(ctx, dataset_id, path):
    """Get details of dataset based on dataset identifier.

    :param ctx:        Combined type of a callback and rei struct
    :param dataset_id: Identifier of dataset
    :param path:       Path to dataset

    :returns: Dict holding objects for the dataset
    """
    # Inialise all attributes
    dataset = {"dataset_id": dataset_id,
               "path": path}

    # Parse dataset_id to get WEPV-items individually
    dataset_parts = dataset_id.split('\t')
    dataset['wave'] = dataset_parts[0]
    dataset['expType'] = dataset_parts[1]
    dataset['experiment_type'] = dataset_parts[1]
    dataset['pseudocode'] = dataset_parts[2]
    dataset['version'] = dataset_parts[3]
    directory = dataset_parts[4]

    dataset['datasetStatus'] = 'scanned'
    dataset['datasetCreateName'] = '==UNKNOWN=='
    dataset['datasetCreateDate'] = 0
    dataset['datasetErrors'] = 0
    dataset['datasetWarnings'] = 0
    dataset['datasetComments'] = 0
    dataset['objects'] = 0
    dataset['objectErrors'] = 0
    dataset['objectWarnings'] = 0

    tl_info = get_dataset_toplevel_objects(ctx, path, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    if is_collection:
        """ dataset is based on a collection """
        tl_collection = tl_objects[0]
        iter = genquery.row_iterator(
            "COLL_NAME, COLL_OWNER_NAME, COLL_CREATE_TIME",
            "COLL_NAME = '" + tl_collection + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            dataset['datasetCreateName'] = row[1]
            dataset['datasetCreateDate'] = time.strftime('%Y-%m-%d', time.localtime(int(row[2])))
            dataset['datasetCreatedByWhen'] = row[1] + ':' + row[2]

        iter = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, count(META_COLL_ATTR_VALUE)",
            "COLL_NAME = '" + tl_collection + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            if row[1] == 'dataset_error':
                dataset['datasetErrors'] += int(row[2])
            if row[1] == 'dataset_warning':
                dataset['datasetWarnings'] += int(row[2])
            if row[1] == 'comment':
                dataset['datasetComments'] += int(row[2])
            if row[1] == 'to_vault_freeze':
                dataset['datasetStatus'] = 'frozen'
            if row[1] == 'to_vault_lock':
                dataset['datasetStatus'] = 'locked'

        iter = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + tl_collection + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            if row[1] == 'object_count':
                dataset['objects'] += int(row[2])
            if row[1] == 'object_errors':
                dataset['objectErrors'] += int(row[2])
            if row[1] == 'object_warnings':
                dataset['objectWarnings'] += int(row[2])
    else:
        # Dataset is based on a dataobject
        # Step through all data objects as found in tl_objects
        objects = 0
        object_errors = 0
        object_warnings = 0
        for tl_object in tl_objects:

            # split tl_object
            tlo = pathutil.chop(tl_object)
            parent = tlo[0]
            base_name = tlo[1]

            objects += 1
            if objects == 1:
                iter = genquery.row_iterator(
                    "DATA_OWNER_NAME, DATA_CREATE_TIME",
                    "COLL_NAME = '" + parent + "' and DATA_NAME = '" + base_name + "' ",
                    genquery.AS_LIST, ctx
                )
                for row in iter:
                    dataset['datasetCreateName'] = row[0]
                    dataset['datasetCreateDate'] = time.strftime('%Y-%m-%d', time.localtime(int(row[1])))
                    dataset['datasetCreatedByWhen'] = row[0] + ':' + row[1]

            iter = genquery.row_iterator(
                "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
                "COLL_NAME = '" + parent + "' and DATA_NAME = '" + base_name + "' ",
                genquery.AS_LIST, ctx
            )
            for row in iter:
                if row[0] == 'error':
                    object_errors += 1
                if row[0] == 'warning':
                    object_warnings += 1
                if objects == 1:
                    # Only look at these items when objects==1 as they are added to each toplevel object present
                    if row[0] == 'dataset_error':
                        dataset['datasetErrors'] += 1
                    if row[0] == 'dataset_warning':
                        dataset['datasetWarnings'] += 1
                    if row[0] == 'comment':
                        dataset['datasetComments'] += 1
                if row[0] == 'to_vault_freeze':
                    dataset['datasetStatus'] = 'frozen'
                if row[0] == 'to_vault_lock':
                    dataset['datasetStatus'] = 'locked'
        dataset['objects'] = objects
        dataset['objectErrors'] = object_errors
        dataset['objectWarnings'] = object_warnings

    return dataset


def get_dataset_toplevel_objects(ctx, root, dataset_id):
    """Returns dict with toplevel object paths and whether is collection based dataset.

    If is a collection - only one object is returned (collection path).
    If not a collection- all objects are returned with full object path.

    :param ctx:        Combined type of a callback and rei struct
    :param root:       Path to a dataset
    :param dataset_id: Identifier of the dataset

    :returns: Dict holding objects for the dataset
    """
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME LIKE '" + root + "%' AND META_COLL_ATTR_NAME = 'dataset_toplevel' "
        "AND META_COLL_ATTR_VALUE = '" + dataset_id + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        return {'is_collection': True,
                'objects': [row[0]]}

    # For dataobject situation gather all object path strings as a list
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME like '" + root + "%' AND META_DATA_ATTR_NAME = 'dataset_toplevel' "
        "AND META_DATA_ATTR_VALUE = '" + dataset_id + "'",
        genquery.AS_LIST, ctx
    )
    objects = []
    for row in iter:
        objects.append(row[1] + '/' + row[0])
    return {'is_collection': False,
            'objects': objects}


@api.make()
def api_intake_scan_for_datasets(ctx, coll):
    """The toplevel of a dataset can be determined by attribute 'dataset_toplevel'
    and can either be a collection or a data_object.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to scan for datasets

    :returns: indication correct
    """

    if _intake_check_authorized_to_scan(ctx, coll):
        _intake_scan_for_datasets(ctx, coll)
    else:
        return {}

    return {"proc_status": "OK"}


@rule.make(inputs=[0], outputs=[1])
def rule_intake_scan_for_datasets(ctx, coll):
    """The toplevel of a dataset can be determined by attribute 'dataset_toplevel'
    and can either be a collection or a data_object.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to scan for datasets

    :returns: indication correct
    """
    if _intake_check_authorized_to_scan(ctx, coll):
        _intake_scan_for_datasets(ctx, coll, tl_datasets_log_target='stdout')
    else:
        return 1

    return 0


def _intake_check_authorized_to_scan(ctx, coll):
    """Checks that user is authorized to scan intake group, either as
       a data manager or as an intake group member.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to scan for datasets

    :returns: boolean - whether user is authorized
    """
    parts = coll.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if (user.is_member_of(ctx, group) or user.is_member_of(ctx, datamanager_group)):
        return True
    else:
        log.write(ctx, "No permissions to scan collection")
        return False


def _intake_scan_for_datasets(ctx, coll, tl_datasets_log_target=''):
    """Internal function for actually running intake scan

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to scan for datasets
    :param tl_datasets_log_target: If in ['stdout', 'serverLog'] logging of toplevel datasets will take place to the specified target

    """
    scope = {"wave": "",
             "experiment_type": "",
             "pseudocode": ""}
    found_datasets = []
    log.write(ctx, 'SCAN COLLECTION - START')
    found_datasets = intake_scan.intake_scan_collection(ctx, coll, scope, False, found_datasets)
    log.write(ctx, 'SCAN COLLECTION - END')

    if tl_datasets_log_target in ['stdout', 'serverLog']:
        for subscope in found_datasets:
            try:
                version = subscope['version']
            except KeyError:
                version = 'Raw'
            ctx.writeLine(tl_datasets_log_target, ("Found dataset toplevel collection: " + 
                                                  "W<" + subscope['wave'] + 
                                                  "> E<" + subscope['experiment_type'] + 
                                                  "> P<" + subscope['pseudocode'] + 
                                                  "> V<" + version + 
                                                  "> D<" + subscope['dataset_directory'] + 
                                                  ">"))

    log.write(ctx, 'INTAKE CHECK DATASETS - START')
    intake_scan.intake_check_datasets(ctx, coll)
    log.write(ctx, 'INTAKE CHECK DATASETS - END')


@api.make()
def api_intake_lock_dataset(ctx, path, dataset_ids):
    """Lock datasets as an indication it can be 'frozen' for it to progress to vault.

    Lock = datamanager only

    :param ctx:         Combined type of a callback and rei struct
    :param path:        Collection for which to lock a specific dataset id
    :param dataset_ids: Comma separated identifiers of datasets to be locked

    :returns: indication correct
    """
    # check permissions - datamanager only
    parts = path.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if not user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "No permissions to lock dataset")
        return {"proc_status": "NOK"}

    for dataset_id in dataset_ids.split(','):
        intake_lock.intake_dataset_lock(ctx, path, dataset_id)

    return {"proc_status": "OK"}


@api.make()
def api_intake_unlock_dataset(ctx, path, dataset_ids):
    """Unlock a dataset to remove the indication so it can be 'frozen' for it to progress to vault

    Unlock = datamanager only

    :param ctx:         Combined type of a callback and rei struct
    :param path:        Collection for which to lock a specific dataset id
    :param dataset_ids: Comma separated identifiers of datasets to be locked

    :returns: indication correct
    """
    # check permissions - datamanager only
    parts = path.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if not user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "No permissions to unlock dataset")
        return {"proc_status": "NOK"}

    for dataset_id in dataset_ids.split(','):
        intake_lock.intake_dataset_unlock(ctx, path, dataset_id)

    return {"proc_status": "OK"}


@api.make()
def api_intake_dataset_add_comment(ctx, study_id, dataset_id, comment):
    """Add a comment to a dataset.

    :param ctx:        Combined type of a callback and rei struct
    :param study_id:   Id of the study given dataset belongs to
    :param dataset_id: Identifier of the dataset to add a comment to
    :param comment:    Comment as added by user

    :returns: indication correct
    """
    coll = '/' + user.zone(ctx) + '/home/grp-intake-' + study_id
    log.write(ctx, 'INTAKE COLLECTION')
    log.write(ctx, coll)

    # check permissions - can be researcher or datamanager
    parts = coll.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if not (user.is_member_of(ctx, group) or user.is_member_of(ctx, datamanager_group)):
        log.write(ctx, "No permissions to scan collection")
        return {}

    tl_info = get_dataset_toplevel_objects(ctx, coll, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    timestamp = int(time.time())  # int(datetime.timestamp(datetime.now()))

    comment_data = user.name(ctx) + ':' + str(timestamp) + ':' + comment

    log.write(ctx, comment_data)

    for tl in tl_objects:
        if is_collection:
            avu.associate_to_coll(ctx, tl, 'comment', comment_data)
        else:
            avu.associate_to_data(ctx, tl, 'comment', comment_data)

    return {'user': user.name(ctx), 'timestamp': time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(timestamp)), 'comment': comment}


@api.make()
def api_intake_dataset_get_details(ctx, coll, dataset_id):
    """Get all details for a dataset (errors/warnings, scanned by who/when, comments, file tree).

    1) Errors/warnings
    2) Comments
    3) Tree view of files within dataset.

    :param ctx:        Combined type of a callback and rei struct
    :param coll:       Collection to start from
    :param dataset_id: Identifier of the dataset to get details for

    :returns: dictionary with all dataset data
    """
    # check permissions - can be researcher or datamanager
    parts = coll.split('/')
    group = parts[3]
    datamanager_group = group.replace("-intake-", "-datamanager-", 1)

    if not (user.is_member_of(ctx, group) or user.is_member_of(ctx, datamanager_group)):
        log.write(ctx, "No permissions to scan collection")
        return {}

    tl_info = get_dataset_toplevel_objects(ctx, coll, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    scanned = ''
    comments = []
    dataset_warnings = []
    dataset_errors = []
    files = {}
    for tl in tl_objects:
        if is_collection:
            coll = tl
            # Dataset based on a collection
            iter = genquery.row_iterator(
                "META_COLL_ATTR_VALUE, META_COLL_ATTR_NAME, order_asc(META_COLL_MODIFY_TIME)",
                "COLL_NAME = '{}' and META_COLL_ATTR_NAME in ('dataset_error', 'dataset_warning', 'comment')".format(coll),
                genquery.AS_LIST, ctx
            )
            for row in iter:
                if row[1] == 'dataset_error':
                    dataset_errors.append(row[0])
                elif row[1] == 'dataset_warning':
                    dataset_warnings.append(row[0])
                else:
                    comments.append(row[0])

            # Scanned by/when
            iter = genquery.row_iterator(
                "META_DATA_ATTR_VALUE",
                "META_DATA_ATTR_NAME = 'scanned' AND COLL_NAME = '{}'".format(coll),
                genquery.AS_LIST, ctx
            )
            for row in iter:
                scanned = row[0]
                break

            break
        else:
            # Dataset is based on a data object
            parts = pathutil.chop(tl)
            coll = parts[0]
            file = parts[1]
            iter = genquery.row_iterator(
                "META_DATA_ATTR_VALUE, META_DATA_ATTR_NAME, order_asc(META_DATA_MODIFY_TIME)",
                "COLL_NAME = '{}' AND DATA_NAME = '{}' and META_DATA_ATTR_NAME in ('dataset_error','dataset_warning','comment', 'scanned')".format(coll, file),
                genquery.AS_LIST, ctx
            )
            for row in iter:
                if row[1] == 'dataset_error':
                    dataset_errors.append(row[0])
                elif row[1] == 'dataset_warning':
                    dataset_warnings.append(row[0])
                elif row[1] == 'scanned':
                    scanned = row[0]
                else:
                    comments.append(row[0])

            # do it only once - all data is gathered in the first run
            break

    level = '0'
    files = coll_objects(ctx, level, coll, dataset_id)

    log.write(ctx, files)

    if len(scanned.split(':')) != 2:
        # Retrieve scannedby/when information in a different way
        dataset = get_dataset_details(ctx, dataset_id, coll)
        scanned = dataset['datasetCreatedByWhen']

    return {"files": files,
            # "is_collection": is_collection,
            # "tlobj": tl_objects,
            "scanned": scanned,
            "comments": comments,
            "dataset_warnings": dataset_warnings,
            "dataset_errors": dataset_errors}


def coll_objects(ctx, level, coll, dataset_id):
    """Recursive function to pass entire folder/file structure in such that frontend
    can do something useful with it including errors/warnings on object level

    :param ctx:   Combined type of a callback and rei struct
    :param level: Level in hierarchy (tree)
    :param coll:  Collection to collect
    :param dataset_id: id of the dataset involved

    :returns: Tree of collections and files
    """
    # First get the sub collections
    counter = 0
    files = {}

    # COLLECTIONS
    iter = genquery.row_iterator(
        "COLL_NAME, COLL_ID",
        "COLL_PARENT_NAME = '{}' AND META_COLL_ATTR_NAME = 'dataset_id' AND META_COLL_ATTR_VALUE = '{}'".format(coll, dataset_id),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # files(pathutil.basename(row[0]))
        node = {}
        node['name'] = pathutil.basename(row[0])
        node['isFolder'] = True
        node['parent_id'] = level
        warnings = []
        errors = []
        # Per collection add errors/warnings from scan process
        iter2 = genquery.row_iterator(
            "META_COLL_ATTR_VALUE, META_COLL_ATTR_NAME",
            "META_COLL_ATTR_NAME in ('warning', 'error') AND COLL_ID = '{}'".format(row[1]),
            genquery.AS_LIST, ctx
        )
        for row2 in iter2:
            if row[1] == 'error':
                errors.append(row2[0])
            else:
                warnings.append(row2[0])
        node['errors'] = errors
        node['warnings'] = warnings

        files[level + "." + str(counter)] = node

        files.update(coll_objects(ctx, level + "." + str(counter), row[0], dataset_id))

        counter += 1

    # DATA OBJECTS
    iter = genquery.row_iterator(
        "DATA_NAME, DATA_ID",
        "COLL_NAME = '{}' AND META_DATA_ATTR_NAME = 'dataset_id' AND META_DATA_ATTR_VALUE = '{}'".format(coll, dataset_id),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        node = {}
        node['name'] = row[0]
        node['isFolder'] = False
        node['parent_id'] = level
        # Per data object add errors/warnings from scan process
        iter2 = genquery.row_iterator(
            "META_DATA_ATTR_VALUE, META_DATA_ATTR_NAME",
            "META_DATA_ATTR_NAME in ('warning', 'error') AND DATA_ID = '{}'".format(row[1]),
            genquery.AS_LIST, ctx
        )
        warnings = []
        errors = []
        for row2 in iter2:
            if row2[1] == 'error':
                errors.append(row2[0])
            else:
                warnings.append(row2[0])
        node['errors'] = errors
        node['warnings'] = warnings

        files[level + "." + str(counter)] = node

        counter += 1

    return files


# Reporting / export functions
@api.make()
def api_intake_report_vault_dataset_counts_per_study(ctx, study_id):
    """Get the count of datasets wave/experimenttype.

    In the vault a dataset is always located in a folder.
    Therefore, looking at the folders only is enough.

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Study id

    :returns: Dictionary with relevant aggregated counts
    """
    # check permissions - datamanager only
    datamanager_group = "grp-datamanager-" + study_id

    if not user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "No permissions for reporting functionality")
        return {}

    return intake_dataset.intake_youth_dataset_counts_per_study(ctx, study_id)


@api.make()
def api_intake_report_vault_aggregated_info(ctx, study_id):
    """Collects the following information for Raw, Processed datasets.
    Including a totalisation of this all (Raw/processed is kept in VERSION).

    -Total datasets
    -Total files
    -Total file size
    -File size growth in a month
    -Datasets growth in a month
    -Pseudocodes  (distinct)

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Study id

    :returns: Dictionary with data for analysis
    """
    log.write(ctx, 'ERIN VAULT AGGREGATED INFO')
    # check permissions - datamanager only
    datamanager_group = "grp-datamanager-" + study_id

    if not user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "No permissions for reporting functionality")
        return {}

    return intake_dataset.vault_aggregated_info(ctx, study_id)


@api.make()
def api_intake_report_export_study_data(ctx, study_id):
    """Find all datasets in the vault for $studyID.

    Include file count and total file size as well as dataset meta data version, experiment type, pseudocode and wave

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Study id to get a report from

    :returns: Study report
    """
    # check permissions - datamanager only
    datamanager_group = "grp-datamanager-" + study_id

    if not user.is_member_of(ctx, datamanager_group):
        log.write(ctx, "No permissions to export data for this study")
        return {}

    return intake_dataset.intake_report_export_study_data(ctx, study_id)
