# -*- coding: utf-8 -*-
"""Functions for intake scanning."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import re
import time

import genquery

import intake
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

    # Let op! Hij moet in de loop blijven TOT alle pseudocode/exp/wave compleet zijn.
    # En zelfs daarna, kunnen waarden nog worden overschreven.

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

        if not (locked_state['locked'] or locked_state['frozen']):
            remove_dataset_metadata(ctx, path, False)
            scan_mark_scanned(ctx, path, False)
        if in_dataset:
            apply_dataset_metadata(ctx, path, scope, False, False)
        else:
            subscope = intake_extract_tokens_from_name(ctx, row[1], row[0], False, scope.copy())

            if intake_tokens_identify_dataset(subscope):
                # We found a top-level dataset data object.
                subscope["dataset_directory"] = row[1]
                apply_dataset_metadata(ctx, path, subscope, False, True)
                # For reporting purposes collect the subscopes
                found_datasets.append(subscope)
            else:
                # subscope["dataset_directory"] = row[1]
                # apply_dataset_metadata(ctx, path, subscope, False, True)
                apply_partial_metadata(ctx, subscope, path, False)
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

            if not (locked_state['locked'] or locked_state['frozen']):
                remove_dataset_metadata(ctx, path, True)

                subscope = scope.copy()
                child_in_dataset = in_dataset

                if in_dataset:  # initially is False
                    # Safeguard original data
                    prev_scope = subscope.copy()
                    # Extract tokens
                    intake_extract_tokens_from_name(ctx, path, dirname, True, subscope)

                    new_deeper_dataset_toplevel = False
                    if not (prev_scope['pseudocode'] == subscope['pseudocode']
                            and prev_scope['experiment_type'] == subscope['experiment_type']
                            and prev_scope['wave'] == subscope['wave']):
                        # Found a deeper lying dataset with more specific attributes
                        # Prepwork for being able to create a dataset_id
                        prev_scope['directory'] = prev_scope["dataset_directory"]
                        if 'version' not in prev_scope:
                            prev_scope['version'] = 'Raw'

                        avu.rm_from_coll(ctx, prev_scope['directory'], 'dataset_toplevel', dataset_make_id(prev_scope))

                        # set flag correctly for creating of new toplevel
                        new_deeper_dataset_toplevel = True

                    subscope["dataset_directory"] = path
                    apply_dataset_metadata(ctx, path, subscope, True, new_deeper_dataset_toplevel)

                    scan_mark_scanned(ctx, path, True)
                else:
                    subscope = intake_extract_tokens_from_name(ctx, path, dirname, True, subscope)

                    if intake_tokens_identify_dataset(subscope):
                        child_in_dataset = True
                        # We found a top-level dataset collection.
                        subscope["dataset_directory"] = path
                        apply_dataset_metadata(ctx, path, subscope, True, True)
                        # For reporting purposes collect the subscopes
                        found_datasets.append(subscope)
                    else:
                        apply_partial_metadata(ctx, subscope, path, True)
                # Go a level deeper
                found_datasets = intake_scan_collection(ctx, path, subscope, child_in_dataset, found_datasets)

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


def intake_tokens_identify_dataset(tokens):
    """Check whether the tokens gathered so far are sufficient for indentifyng a dataset.

    :param tokens: A key-value list of tokens

    :returns: Returns whether a dataset is identified
    """
    required = ['wave', 'experiment_type', 'pseudocode']  # version is optional

    missing = 0
    for req_token in required:
        # required tokens must be present and must have a value
        if req_token not in tokens or tokens[req_token] == "":
            missing = missing + 1

    return (missing == 0)


def intake_extract_tokens_from_name(ctx, path, name, is_collection, scoped_buffer):
    """Extract one or more tokens from a file / directory name and add dataset information as metadata.
    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to object or collection
    :param name:          Name of object or collection
    :param is_collection: Indicates if object or collection
    :param scoped_buffer: Holds dataset buffer with prefilled keys
    :returns: Returns extended scope buffer
    """
    name_without_ext = os.path.splitext(name)[0]
    parts = re.split("[_-]", name_without_ext)
    for part in parts:
        scoped_buffer.update(intake_extract_tokens(ctx, part))
    return scoped_buffer


def intake_extract_tokens(ctx, string):
    """Extract tokens from a string and return as dict.

    :param ctx:    Combined type of a callback and rei struct
    :param string: Token of which to be determined whether experiment type, version etc

    :returns: Returns found kv's
    """
    exp_types = ["pci",
                 "echo",
                 "facehouse",
                 "faceemo",
                 "coherence",
                 "infprogap",
                 "infsgaze",
                 "infpop",
                 # "mriinhibition",
                 # "mriemotion",
                 # "mockinhibition",
                 "chprogap",
                 "chantigap",
                 "chsgaze",
                 "pciconflict",
                 "pcivacation",
                 "peabody",
                 "discount",
                 "cyberball",
                 "trustgame",
                 "other",
                 # MRI:
                 "inhibmockbehav",
                 "inhibmribehav",
                 "emotionmribehav",
                 "emotionmriscan",
                 "anatomymriscan",
                 "restingstatemriscan",
                 "dtiamriscan",
                 "dtipmriscan",
                 "mriqcreport",
                 "mriqceval",
                 "vasmri",
                 "vasmock",
                 #
                 "looklisten",
                 "handgame",
                 "infpeabody",
                 "delaygratification",
                 "dtimriscan",
                 "inhibmriscan",
                 # 16-Apr-2019 fbyoda email request new exp type:
                 "chdualet",
                 # 15-Feb-2021 fbyoda email request new exp type:
                 "functionalmriscan",
                 "infdualet",
                 "vrbartbehav",
                 "infssat"]

    str_lower = string.lower()
    str_upper = string.upper()
    str_for_pseudocode_test = string.split('.')[0]
    str_for_version_test = string.translate(None, ".")

    foundKVs = {}
    if re.match('^[0-9]{1,2}[wmy]$', str_lower) is not None:
        # String contains a wave.
        # Wave validity is checked later on in the dataset checks.
        foundKVs["wave"] = str_lower
    elif re.match('^[bap][0-9]{5}$', str_for_pseudocode_test.lower()) is not None:
        # String contains a pseudocode.
        foundKVs["pseudocode"] = str_upper[0:len(str_for_pseudocode_test)]
    elif re.match('^[Vv][Ee][Rr][A-Z][a-zA-Z0-9-]*$', str_for_version_test) is not None:
        foundKVs["version"] = string[3:len(string)]
    elif str_lower in exp_types:
        foundKVs["experiment_type"] = str_lower

    return foundKVs


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


def apply_dataset_metadata(ctx, path, scope, is_collection, is_top_level):
    """Apply dataset metadata to an object in a dataset.

    :param ctx:           Combined type of a callback and rei struct
    :param path:          Path to the object
    :param scope:         A scanner scope containing WEPV values
    :param is_collection: Whether the object is a collection
    :param is_top_level:  If true, a dataset_toplevel field will be set on the object
    """

    if "version" not in scope:
        version = "Raw"
    else:
        version = scope["version"]

    subscope = {"wave": scope["wave"],
                "experiment_type":  scope["experiment_type"],
                "pseudocode": scope["pseudocode"],
                "version": version,
                "directory": scope["dataset_directory"]}

    subscope["dataset_id"] = dataset_make_id(subscope)

    log.write(ctx, 'APPLY DATASET META')
    log.write(ctx, subscope)

    # add all keys to this to this level

    for key in subscope:
        if subscope[key]:
            if is_collection:
                avu.set_on_coll(ctx, path, key, subscope[key])
            else:
                avu.set_on_data(ctx, path, key, subscope[key])

    if is_top_level:
        # Add dataset_id to dataset_toplevel
        if is_collection:
            avu.set_on_coll(ctx, path, 'dataset_toplevel', subscope["dataset_id"])
        else:
            avu.set_on_data(ctx, path, 'dataset_toplevel', subscope["dataset_id"])


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


def dataset_add_error(ctx, top_levels, is_collection_toplevel, text):
    """Add a dataset error to all given dataset toplevels.

    :param ctx:                    Combined type of a callback and rei struct
    :param top_levels:             A list of toplevel datasets
    :param is_collection_toplevel: Indication of whether it is a collection or object
    :param text:                   Error text
    """
    for tl in top_levels:
        if is_collection_toplevel:
            avu.associate_to_coll(ctx, tl, "dataset_error", text)
        else:
            avu.associate_to_data(ctx, tl, "dataset_error", text)


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
        dataset_add_error(ctx, tl_objects, is_collection, "Wave, experiment type or pseudo-ID missing")

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


def dataset_make_id(scope):
    """Construct a dateset based on WEPV and directory.

    :param scope: Create a dataset id

    :returns: Dataset identifier
    """
    return scope['wave'] + '\t' + scope['experiment_type'] + '\t' + scope['pseudocode'] + '\t' + scope['version'] + '\t' + scope['directory']


def dataset_parse_id(dataset_id):
    """Parse a dataset into its consructive data.

    :param dataset_id: Dataset identifier

    :returns: Dataset as a dict
    """
    dataset_parts = dataset_id.split('\t')
    dataset = {}
    dataset['wave'] = dataset_parts[0]
    dataset['experiment_type'] = dataset_parts[1]  # Is DIT NOG ERGENS GOED VOOR
    dataset['expType'] = dataset_parts[1]
    dataset['pseudocode'] = dataset_parts[2]
    dataset['version'] = dataset_parts[3]
    dataset['directory'] = dataset_parts[4]

    return dataset
