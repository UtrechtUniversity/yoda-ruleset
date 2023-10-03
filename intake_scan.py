# -*- coding: utf-8 -*-
"""Functions for intake scanning."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

import genquery

import intake
from intake_utils import dataset_parse_id, intake_scan_get_metadata_update
from util import *


def intake_scan_collection(ctx, root, scope, in_dataset, found_datasets):
    """Recursively scan a directory in a Youth Cohort intake.

    :param ctx:    Combined type of a callback and rei struct
    :param root:   the directory to scan
    :param scope:     a scoped kvlist buffer
    :param in_dataset: whether this collection is within a dataset collection
    :param found_datasets: collection of subscopes that were found in order to report toplevel datasets in the scanning process

    :returns: Found datasets
    """

    # Loop until pseudocode, experiment type and wave are complete.
    # But the found values can be overwritten when deeper levels are found.

    # Scan files under root
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME = '" + root + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        path = row[1] + '/' + row[0]

        # Determene lock state for object (no collectoin
        locked_state = object_is_locked(ctx, path, False)

        if locked_state['locked'] or locked_state['frozen']:
            continue

        remove_dataset_metadata(ctx, path, False)
        scan_mark_scanned(ctx, path, False)

        parent_in_dataset = in_dataset
        metadata_update = intake_scan_get_metadata_update(ctx, path, False, in_dataset, scope)

        if metadata_update["in_dataset"]:
            apply_dataset_metadata(ctx, path, metadata_update["new_metadata"], False)
            if not parent_in_dataset:
                # We found a top-level dataset data object.
                found_datasets.append(metadata_update["new_metadata"])
        else:
            apply_partial_metadata(ctx, metadata_update["new_metadata"], path, False)
            avu.set_on_data(ctx, path, "unrecognized", "Experiment type, wave or pseudocode missing from path")

    # Scan collections under root
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '" + root + "'",
        genquery.AS_LIST, ctx
    )
    counter = 0
    for row in iter:
        path = row[0]
        counter = counter + 1
        dirname = pathutil.basename(path)

        if dirname != '/':
            # get locked /frozen status
            locked_state = object_is_locked(ctx, path, True)

            if locked_state['locked'] or locked_state['frozen']:
                continue

            remove_dataset_metadata(ctx, path, True)
            scan_mark_scanned(ctx, path, True)

            parent_in_dataset = in_dataset
            metadata_update = intake_scan_get_metadata_update(ctx, path, True, in_dataset, scope)

            if metadata_update["in_dataset"]:
                apply_dataset_metadata(ctx, path, metadata_update["new_metadata"], True)
                if not parent_in_dataset:
                    # We found a new top-level dataset data object.
                    found_datasets.append(metadata_update["new_metadata"])
            else:
                apply_partial_metadata(ctx, metadata_update["new_metadata"], path, True)

            found_datasets = intake_scan_collection(ctx,
                                                    path,
                                                    metadata_update["new_metadata"],
                                                    parent_in_dataset or metadata_update["in_dataset"],
                                                    found_datasets)

    return found_datasets


def object_is_locked(ctx, path, is_collection):
    """Returns whether given object in path (collection or dataobject) is locked or frozen

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to object or collection
    :param is_collection: Whether path contains a collection or data object

    :returns: Returns locked state
    """
    locked_state = {"locked": False,
                    "frozen": False}

    if is_collection:
        iter = genquery.row_iterator(
            "META_COLL_ATTR_NAME",
            "COLL_NAME = '" + path + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            if row[0] in ['to_vault_lock', 'to_vault_freeze']:
                locked_state['locked'] = True
                if row[0] == 'to_vault_freeze':
                    locked_state['frozen'] = True
    else:
        parent_coll = pathutil.dirname(path)
        iter = genquery.row_iterator(
            "META_DATA_ATTR_NAME",
            "COLL_NAME = '" + parent_coll + "' AND DATA_NAME = '" + pathutil.basename(path) + "'",
            genquery.AS_LIST, ctx
        )
        # return locked_state
        for row in iter:
            if row[0] in ['to_vault_lock', 'to_vault_freeze']:
                locked_state['locked'] = True
                if row[0] == 'to_vault_freeze':
                    locked_state['frozen'] = True

    return locked_state


def remove_dataset_metadata(ctx, path, is_collection):
    """Remove all intake metadata from dataset.

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to collection or data object
    :param is_collection: Whether is a collection or data object
    """
    intake_metadata = ["wave",
                       "experiment_type",
                       "pseudocode",
                       "version",
                       "dataset_id",
                       "dataset_toplevel",
                       "error",
                       "warning",
                       "dataset_error",
                       "dataset_warning",
                       "unrecognized",
                       "object_count",
                       "object_errors",
                       "object_warnings"]
    intake_metadata_set = set(intake_metadata)

    # Add the following two lines to remove accumulated metadata during testing.
    # "comment"
    # "scanned"]

    if is_collection:
        iter = genquery.row_iterator(
            "COLL_ID, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + path + "'",
            genquery.AS_LIST, ctx
        )
    else:
        iter = genquery.row_iterator(
            "DATA_ID, META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
            "COLL_NAME = '" + pathutil.dirname(path) + "' AND DATA_NAME = '" + pathutil.basename(path) + "'",
            genquery.AS_LIST, ctx
        )

    for _row in iter:
        metadata_name = _row[1]
        if metadata_name in intake_metadata_set:
            if is_collection:
                try:
                    avu.rmw_from_coll(ctx, path, metadata_name, '%')
                except Exception as e:
                    log.write(ctx, "Warning: unable to remove metadata attr {} from {}".format(metadata_name, path))
                    log.write(ctx, "Removing metadata failed with exception {}".format(str(e)))
            else:
                try:
                    avu.rmw_from_data(ctx, path, metadata_name, '%')
                except Exception as e:
                    log.write(ctx, "Warning: unable to remove metadata attr {} from {}".format(metadata_name, path))
                    log.write(ctx, "Removing metadata failed with exception {}".format(str(e)))


def scan_mark_scanned(ctx, path, is_collection):
    """Sets the username of the scanner and a timestamp as metadata on the scanned object.

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path on which to add scan indication to
    :param is_collection: Is scanned object a collection?
    """
    timestamp = int(time.time())
    user_and_timestamp = user.name(ctx) + ':' + str(timestamp)  # str(datetime.date.today())

    if is_collection:
        avu.set_on_coll(ctx, path, 'scanned', user_and_timestamp)
    else:
        avu.set_on_data(ctx, path, 'scanned', user_and_timestamp)


def apply_dataset_metadata(ctx, path, scope, is_collection):
    """Apply dataset metadata to an object in a dataset.

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to the object
    :param scope:         A scanner scope containing WEPV values
    :param is_collection: Whether the object is a collection
    """
    for key in scope:
        if scope[key]:
            if is_collection:
                avu.set_on_coll(ctx, path, key, scope[key])
            else:
                avu.set_on_data(ctx, path, key, scope[key])


def apply_partial_metadata(ctx, scope, path, is_collection):
    """Apply any available id component metadata to the given object.

    To be called only for objects outside datasets. When inside a dataset
    (or at a dataset toplevel), use intake_apply_dataset_metadata() instead.

    :param ctx:           Combined type of a callback and rei struct
    :param scope:         A scanner scope containing some WEPV values
    :param path:          Path to the object
    :param is_collection: Whether the object is a collection
    """
    keys = ['wave', 'experiment_type', 'pseudocode', 'version']
    for key in keys:
        if key in scope:
            if scope[key]:
                if is_collection:
                    avu.set_on_coll(ctx, path, key, scope[key])
                else:
                    avu.set_on_data(ctx, path, key, scope[key])


def dataset_add_error(ctx, top_levels, is_collection_toplevel, text, suppress_duplicate_avu_error=False):
    """Add a dataset error to all given dataset toplevels.

    :param ctx:                    Combined type of a callback and rei struct
    :param top_levels:             A list of toplevel datasets
    :param is_collection_toplevel: Indication of whether it is a collection or object
    :param text:                   Error text
    :param suppress_duplicate_avu_error: If an AVU already exists, suppress the irods-error. Allow for this situation

    :raises Exception: Raises exception when associating error to collection or data object fails
    """
    for tl in top_levels:
        if is_collection_toplevel:
            try:
                avu.associate_to_coll(ctx, tl, "dataset_error", text)
            except msi.Error as e:
                # iRODS errorcode 809000 (CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME)
                if suppress_duplicate_avu_error and str(e).find("809000") > -1:
                    log.write(ctx, "Trying to associate dataset_error already present on collection: {}".format(tl))
                    log.write(ctx, "Suppress error handling for AVU: dataset_error - {}".format(text))
                else:
                    raise Exception(e)
        else:
            try:
                avu.associate_to_data(ctx, tl, "dataset_error", text)
            except msi.Error as e:
                # iRODS errorcode 809000 (CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME)
                if suppress_duplicate_avu_error and str(e).find("809000") > -1:
                    log.write(ctx, "Trying to associate dataset_error already present on data object: {}".format(tl))
                    log.write(ctx, "Suppress error handling for AVU: dataset_error - {}".format(text))
                else:
                    raise Exception(e)


def dataset_get_ids(ctx, coll):
    """Find dataset ids under collection.
    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection name for which to find dataset-ids
    :returns: Returns a set of dataset ids
    """
    data_ids = set()

    # Get distinct data_ids
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_DATA_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if row[0]:
            data_ids.add(row[0])

    # Get distinct data_ids
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME LIKE '" + coll + "%' AND META_DATA_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if row[0]:
            data_ids.add(row[0])

    return data_ids


def intake_check_datasets(ctx, root):
    """Run checks on all datasets under root.

    :param ctx:  Combined type of a callback and rei struct
    :param root: The collection to get datasets for
    """
    dataset_ids = dataset_get_ids(ctx, root)
    for dataset_id in dataset_ids:
        intake_check_dataset(ctx, root, dataset_id)


def intake_check_dataset(ctx, root, dataset_id):
    """Run checks on the dataset specified by the given dataset id.

    This function adds warnings and errors to objects within the dataset.

    :param ctx:        Combined type of a callback and rei struct
    :param root:       Collection name
    :param dataset_id: Dataset identifier
    """
    tl_info = intake.get_dataset_toplevel_objects(ctx, root, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    # Check validity of wav
    waves = ["20w", "30w", "0m", "5m", "10m", "3y", "6y", "9y", "12y", "15y"]
    components = dataset_parse_id(dataset_id)
    if components['wave'] not in waves:
        dataset_add_error(ctx, tl_objects, is_collection, "The wave '" + components['wave'] + "' is not in the list of accepted waves")

    # check presence of wave, pseudo-ID and experiment
    if '' in [components['wave'], components['experiment_type'], components['pseudocode']]:
        # Suppress error handing and continue normal processing should a situation arise where Wepv missing is already present on the dataobject/collection
        dataset_add_error(ctx, tl_objects, is_collection, "Wave, experiment type or pseudo-ID missing", True)

    for tl in tl_objects:
        # Save the aggregated counts of #objects, #warnings, #errors on object level

        count = get_aggregated_object_count(ctx, dataset_id, tl)
        if is_collection:
            avu.set_on_coll(ctx, tl, "object_count", str(count))
        else:
            avu.set_on_data(ctx, tl, "object_count", str(count))

        count = get_aggregated_object_error_count(ctx, dataset_id, tl)
        if is_collection:
            avu.set_on_coll(ctx, tl, "object_errors", str(count))
        else:
            avu.set_on_data(ctx, tl, "object_errors", str(count))

        count = 0
        if is_collection:
            avu.set_on_coll(ctx, tl, "object_warnings", str(count))
        else:
            avu.set_on_data(ctx, tl, "object_warnings", str(count))


def get_rel_paths_objects(ctx, root, dataset_id):
    """Get a list of relative paths to all data objects in a dataset.

    :param ctx:        Combined type of a callback and rei struct
    :param root:       Root path of the dataset
    :param dataset_id: Dataset identifier

    :returns: List of objects of relative object paths (e.g. file1.dat, some-subdir/file2.dat...)
    """
    tl_info = intake.get_dataset_toplevel_objects(ctx, root, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    rel_path_objects = []

    # get the correct parent_collection
    try:
        if is_collection:
            parent_coll = tl_objects[0]
        else:
            parent_coll = pathutil.dirname(tl_objects[0])
    except Exception:
        parent_coll = '/'

    """
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME = '" + parent_coll + "' AND META_DATA_ATTR_NAME = 'dataset_id' AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # add objects residing in parent_coll directly to list
        log.write(ctx, "DIRECT " + row[0])
        rel_path_objects.append(row[0])
    """

    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME LIKE '" + parent_coll + "%' AND META_DATA_ATTR_NAME = 'dataset_id' AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # Add objects including relative paths
        rel_path_objects.append(row[1][len(parent_coll):] + '/' + row[0])

    return rel_path_objects


def get_aggregated_object_count(ctx, dataset_id, tl_collection):
    """Return total amounts of objects.

    :param ctx:           Combined type of a callback and rei struct
    :param dataset_id:    Dataset id
    :param tl_collection: Collection name of top level

    :returns: Aggregated object count
    """
    return len(list(genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME like '" + tl_collection + "%' AND META_DATA_ATTR_NAME = 'dataset_id' "
        "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
        genquery.AS_LIST, ctx
    )))


def get_aggregated_object_error_count(ctx, dataset_id, tl_collection):
    """Return total amount of object errors.

    :param ctx:           Combined type of a callback and rei struct
    :param dataset_id:    Dataset id
    :param tl_collection: Collection name of top level

    :returns: Total amount of object errors
    """
    return len(list(genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME like '" + tl_collection + "%' AND META_DATA_ATTR_NAME = 'error' ",
        genquery.AS_LIST, ctx
    )))
