# -*- coding: utf-8 -*-
"""Functions for revision management."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time
import irods_types
import re

from util import *
from util.query import Query
from folder import *


def intake_scan_collection(ctx, root, scope, in_dataset):
    """Recursively scan a directory in a Youth Cohort intake.

    :param[in] root      the directory to scan
    :param[in] scope     a scoped kvlist buffer
    :param[in] inDataset whether this collection is within a dataset collection
    """

    log.write(ctx, "AT ENTRY")
    log.write(ctx, "SCAN OBJECTS: " + root)
    log.write(ctx, scope)
    # Scan files under root
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME = '" + root + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # chop file extension ???? HIER WORDT NIKS MEE GEDAAN
        # uuChopFileExtension(*item>DATANAME, baseName, extension) ??? baseName en extension komen niet terug in oorspronkeljike functie

        path = row[1] + '/' + row[0]

        # Determene lock state for object (no collectoin
        locked_state = object_is_locked(ctx, path, False)

        if not (locked_state['locked'] or locked_state['frozen']):
            remove_dataset_metadata(ctx, path, False)
            scan_mark_scanned(ctx, path, False)
            if not scan_filename_is_valid(ctx, row[0]):
                avu.set_on_data(ctx, path, "error", "File name contains disallowed characters")
        if in_dataset:
            apply_dataset_metadata(ctx, path, scope, False, False)
        else:
            subscope = intake_extract_tokens_from_name(ctx, row[1], row[0], False, scope)

            if intake_tokens_identify_dataset(subscope):
                log.write(ctx, "IS DATASET")
                # We found a top-level dataset data object.
                subscope["dataset_directory"] = row[1]
                apply_dataset_metadata(ctx, path, subscope, False, True)
            else:
                log.write(ctx, "IS NO DATASET")
                apply_partial_metadata(ctx, subscope, path, False)
                avu.set_on_data(ctx, path, "unrecognized", "Experiment type, wave or pseudocode missing from path")

    log.write(ctx, "SCAN COLLECTION: " + root)
    log.write(ctx, scope)
    # Scan collections under root
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '" + root + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        log.write(ctx, 'found colls: ' + row[0])

    counter = 0 
    for row in iter:
        path = row[0]
        counter = counter +1
        dirname = pathutil.basename(path)
        log.write(ctx, str(counter) + "FOUND COLLECTION: " + path)
        log.write(ctx, root)
        log.write(ctx, scope)

        if dirname is not '/':
            # get locked /frozen status
            locked_state = object_is_locked(ctx, path, True)

            if not (locked_state['locked'] or locked_state['frozen']):
                remove_dataset_metadata(ctx, path, True)

                if not scan_filename_is_valid(ctx, dirname):
                    avu.set_on_coll(ctx, path, "error", "Directory name contains disallowed characters")

                subscope = scope.copy()
                child_in_dataset = in_dataset

                if in_dataset: # initially is False
                    apply_dataset_metadata(ctx, path, subscope, True, False)
                    scan_mark_scanned(ctx, path, True)
                else:
                    # uuYcIntakeExtractTokensFromFileName(*item."COLL_NAME", *dirName, true, *subScope);
                    # sub_scope wordt gevuld via extract tokens
                    log.write(ctx, 'COLLECTION')
                    subscope = intake_extract_tokens_from_name(ctx, path, dirname, True, subscope)
                    log.write(ctx, subscope)

                    if intake_tokens_identify_dataset(subscope):
                        log.write(ctx, "IS DATASET")
                        child_in_dataset = True
                        # We found a top-level dataset collection.
                        subscope["dataset_directory"] = path
                        apply_dataset_metadata(ctx, path, subscope, True, True)
                    else:
                        log.write(ctx, "IS NO DATASET")
                        apply_partial_metadata(ctx, subscope, path, True)
                # Go a level deeper
                log.write(ctx, "BEFORE DEEPER LEVEL: " + path)
                log.write(ctx, subscope)
                log.write(ctx, scope)
                intake_scan_collection(ctx, path, subscope, child_in_dataset)
                log.write(ctx, "AFTER DEEPER LEVEL scan")


def scan_filename_is_valid(ctx, name):
    """ Check if a file or directory name contains invalid characters """

    return (re.match('^[a-zA-Z0-9_.-]+$', name) is not None)


def object_is_locked(ctx, path, is_collection):
    """ Returns whether given object in path (collection or dataobject) is locked or frozen """

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
            "COLL_NAME = '" + parent_coll + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            if row[0] in ['to_vault_lock', 'to_vault_freeze']:
                locked_state['locked'] = True
                if row[0] == 'to_vault_freeze':
                    locked_state['frozen'] = True

    return locked_state


def intake_tokens_identify_dataset(tokens):
    """ Check whether the tokens gathered so far are sufficient for indentifyng a dataset.
       returns whether complete or not.

    :param[in]  tokens a key-value list of tokens
    """
    required = ['wave', 'experiment_type', 'pseudocode'] # version is optional

    complete = False
    for req_token in required:
        # required tokens must be present and must have a value
        if req_token not in tokens or tokens[req_token] == "":
            return False
    return True


def intake_extract_tokens_from_name(ctx, path, name, is_collection, scoped_buffer):
    """ Extract one or more tokens from a file / directory name and add dataset
    information as metadata.

    :param[in]     path
    :param[in]     name
    :param[in]     isCollection
    :param[in]     scoped_buffer
    returns extended scope buffer
    """
    # chop of extension
    # base_name = '.'.join(name.split('.'))[:-1]
    if is_collection:
        base_name = name
    else:
        # Dit kan problemen opleveren. Eigenlijk wordt hier de extensie eraf gehaald 
        # Maar niet alle bestanden hebben een extensie en mogelijk wordt dus een deel
        # weggehaald met belangrijke beschrijvende info over de dataset.
        #
        base_name = name # name.rsplit('.', 1)[0]
    parts = base_name.split('_')
    for part in parts:
        subparts = part.split('-')
        for subpart in subparts:
            scoped_buffer.update(intake_extract_tokens(ctx, subpart))
    return scoped_buffer


def intake_extract_tokens(ctx, string):
    """ Extract tokens from a string and return as dict.

    :param[in] string
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
                 "chdualet"]

    str_lower = string.lower()
    str_upper = string.upper()

    foundKVs = {}
    if re.match('^[0-9]{1,2}[wmy]$', str_lower) is not None:
        # String contains a wave.
        # Wave validity is checked later on in the dataset checks.
        foundKVs["wave"] = str_lower
    elif re.match('^[bap][0-9]{5}$', str_lower) is not None:
        # String contains a pseudocode.
        foundKVs["pseudocode"] = str_upper[0:len(string)]
    elif re.match('^[Vv][Ee][Rr][A-Z][a-zA-Z0-9-]*$', string) is not None:
        foundKVs["version"] = string[3:len(string)]
    else:
        if str_lower in exp_types:
            foundKVs["experiment_type"] = string

    return foundKVs


def remove_dataset_metadata(ctx, path, is_collection):
    """ Remove all intake metadata from dataset """
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

    for row in iter:
        for md_key in intake_metadata:
            if is_collection:
                log.write(ctx, md_key + ' => ' + path)
                try:
                    avu.rmw_from_coll(ctx, path, md_key, '%')
                except Exception as e:
                    continue
            else:
                try:
                    avu.rmw_from_data(ctx, path, md_key, '%')
                except Exception as e:
                    continue


def scan_mark_scanned(ctx, path, is_collection):
    """ Sets the username of the scanner and a timestamp as metadata on the scanned object.

    :param[in] path
    :param[in] is_collection
    """
    #import datetime
    # Get datetime of tomorrow.
    #tomorrow = datetime.date.today() + datetime.timedelta(1)

    # Convert tomorrow to unix timestamp.
    #return int(tomorrow.strftime("%s"))

    timestamp = int(time.time())
    user_and_timestamp = user.name(ctx) + ':' + str(timestamp) #str(datetime.date.today())

    if is_collection:
        avu.set_on_coll(ctx, path, 'scanned', user_and_timestamp)
    else:
        avu.set_on_data(ctx, path, 'scanned', user_and_timestamp)


def apply_dataset_metadata(ctx, path, scope, is_collection, is_top_level):
    """ Apply dataset metadata to an object in a dataset.

    :param[in] path         path to the object
    :param[in] scope        a scanner scope containing WEPV values
    :param[in] is_collection whether the object is a collection
    :param[in] is_top_level   if true, a dataset_toplevel field will be set on the object
    """

#    if is_collection:
#        avu.set_on_coll(ctx, )
#    else:
#        avu.set_on_data(ctx, )

    if not "version" in scope:
        version = "Raw"
    else:
        version = scope["version"]

    subscope = {"wave": scope["wave"],
                "experiment_type":  scope["experiment_type"],
                "pseudocode": scope["pseudocode"],
                "version": version,
                "directory": scope["dataset_directory"],

    }

    subscope["dataset_id"] = dataset_make_id(subscope)

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
    """ Apply any available id component metadata to the given object.
    To be called only for objects outside datasets. When inside a dataset
    (or at a dataset toplevel), use intake_apply_dataset_metadata() instead.

    :param[in] scope        a scanner scope containing some WEPV values
    :param[in] path         path to the object
    :param[in] is_collection whether the object is a collection
    """
    keys = ['wave', 'experiment_type', 'pseudocode', 'version']
    for key in keys:
        if key in scope:
            if scope[key]:
                if is_collection:
                    avu.set_on_coll(ctx, path, key, scope[key])
                else:
                    avu.set_on_data(ctx, path, key, scope[key])


def dataset_add_warning(ctx, top_levels, is_collection_toplevel, text):
    """ Add a dataset warning to all given dataset toplevels.
    :param[in] toplevels
    :param[in] isCollectionToplevel
    :param[in] text
    """
    for tl in top_levels:
        if is_collection_toplevel:
            avu.associate_to_coll(ctx, tl, "dataset_warning", text)
        else:
            avu.associate_to_data(ctx, tl, "dataset_warning", text)


def dataset_add_error(ctx, top_levels, is_collection_toplevel, text):
    """ Add a dataset error to all given dataset toplevels.
    :param[in] toplevels
    :param[in] isCollectionToplevel
    :param[in] text
    """
    for tl in top_levels:
        if is_collection_toplevel:
            avu.associate_to_coll(ctx, tl, "dataset_error", text)
        else:
            avu.associate_to_data(ctx, tl, "dataset_error", text)


def dataset_get_ids(ctx, coll):
    """ Find dataset ids under coll

    :param[in]  root
    returns ids  a list of dataset ids
    """
    data_ids = []

    # Get distinct data_ids
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_DATA_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if row[0]:
            data_ids.append(row[0])

    # Get distinct data_ids
    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME LIKE '" + coll + "%' AND META_DATA_ATTR_NAME = 'dataset_id' ",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if row[0]: # CHECK FOR DUPLICATES???
            data_ids.append(row[0])

    return data_ids


def intake_check_datasets(ctx, root):
    """ Run checks on all datasets under root.

    :param[in] root
    """
    dataset_ids = dataset_get_ids(ctx, root)
    for dataset_id in dataset_ids:
        intake_check_dataset(ctx, root, dataset_id)


def intake_check_dataset(ctx, root, dataset_id):
    """ Run checks on the dataset specified by the given dataset id.

    This function adds warnings and errors to objects within the dataset.

    :param[in] root
    :param[in] id
    """
    tl_info = get_dataset_toplevel_objects(ctx, root, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    intake_check_generic(ctx, root, dataset_id, tl_objects, is_collection)

    id_components = dataset_parse_id(dataset_id)

    # specific check
    if id_components["experiment_type"].lower() == "echo":
        intake_check_et_echo(ctx, root, dataset_id, tl_objects, is_collection)  # toplevels

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

        count = get_aggregated_object_warning_count(ctx, dataset_id, tl)
        if is_collection:
            avu.set_on_coll(ctx, tl, "object_warnings", str(count))
        else:
            avu.set_on_data(ctx, tl, "object_warnings", str(count))


def intake_check_generic(ctx, root, dataset_id, toplevels, is_collection):
    """ Run checks that must be applied to all datasets regardless of WEPV values.

    :param[in] root
    :param[in] dataset_id           the dataset id to check
    :param[in] toplevels    a list of toplevel objects for this dataset id
    :param[in] isCollection
    """
    # Check validity of wav
    waves = ["20w", "30w","0m", "5m", "10m", "3y", "6y", "9y", "12y", "15y"]
    components = dataset_parse_id(dataset_id)
    if components['wave'] not in waves:
        dataset_add_error(ctx, toplevels, is_collection, "The wave '" + components['wave'] + "' is not in the list of accepted waves")


def intake_check_et_echo(ctx, root, dataset_id, toplevels, is_collection):
    """ Run checks specific to the Echo experiment type.
    :param[in] root
    :param[in] id           the dataset id to check
    :param[in] toplevels    a list of toplevel objects for this dataset id
    :param[in] is_collection
    """
    objects = get_rel_paths_objects(ctx, root, dataset_id)

    try:
        if is_collection:
            dataset_parent = toplevels[0]
        else:
            dataset_parent = pathutil.dirname(toplevels[0])
    except Exception as e:
        dataset_parent = root

    intake_check_file_count(ctx, dataset_parent, toplevels, is_collection, objects, 'I0000000.index.jpg', '(.*/)?I[0-9]{7}\.index\.jpe?g', 13, -1)
    intake_check_file_count(ctx, dataset_parent, toplevels, is_collection, objects, 'I0000000.raw', '(.*/)?I[0-9]{7}\.raw', 7, -1)
    intake_check_file_count(ctx, dataset_parent, toplevels, is_collection, objects, 'I0000000.dcm', '(.*/)?I[0-9]{7}\.dcm', 6, -1)
    intake_check_file_count(ctx, dataset_parent, toplevels, is_collection, objects, 'I0000000.vol', '(.*/)?I[0-9]{7}\.vol', 6, -1)


def get_rel_paths_objects(ctx, root, dataset_id):
    """Get a list of relative paths to all data objects in a dataset.
    :param[in]  root
    :param[in]  dataset_id
    returns a list of objects of relative object paths (e.g. file1.dat, some-subdir/file2.dat...)
    """
    tl_info = get_dataset_toplevel_objects(ctx, root, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']

    rel_path_objects = []

    # get the correct parent_collection
    try:
        if is_collection:
            parent_coll = tl_objects[0]
        else:
            parent_coll = pathutil.dirname(tl_objects[0])
    except Exception as e:
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


def intake_check_file_count(ctx, dataset_parent, toplevels, is_collection_toplevel, objects, pattern_human, pattern_regex, min, max):
    """ Check if a certain filename pattern has enough occurrences in a dataset.

    Adds a warning if the match count is out of range.

    NOTE: Currently, patterns must match the full relative object path.
       At the time of writing, Echo is the only experiment type we run this
       check for, and it is a flat dataset without subdirectories, so it makes
       no difference there.

       For other experiment types it may be desirable to match patterns with
       basenames instead of paths. In this case the currently commented-out
       code in this function can be used.

    :param[in] datasetParent        either the dataset collection or the first parent of a data-object dataset toplevel
    :param[in] toplevels            a list of toplevel objects
    :param[in] isCollectionToplevel
    :param[in] objects              a list of dataset object paths relative to the datasetParent parameter
    :param[in] patternHuman         a human-readable pattern (e.g.: 'I0000000.raw')
    :param[in] patternRegex         a regular expression that matches filenames (e.g.: 'I[0-9]{7}\.raw')
    :param[in] min                  the minimum amount of occurrences. set to -1 to disable minimum check.
    :param[in] max                  the maximum amount of occurrences. set to -1 to disable maximum check.
    """
    count = 0
    for path in objects:
        log.write(ctx, path)
        if re.match(pattern_regex, path) is not None:
            count += 1
            log.write(ctx, '##intake_check_file_count ' + str(count))

    # count = count / 2

    if min!=-1 and count < min:
        text = "Expected at least " + str(min) + " files of type '" + pattern_human + "', found " + str(count)
        log.write(ctx, '##' + text)
        dataset_add_warning(ctx, toplevels, is_collection_toplevel, text)
    if max!=-1 and count > max:
        text = "Expected at most " + str(max) + " files of type '" + pattern_human + "', found " + str(count)
        log.write(ctx, '##' + text)
        dataset_add_warning(ctx, toplevels, is_collection_toplevel, text)


def get_aggregated_object_count(ctx, dataset_id, tl_collection):
    """ return total amounts of objects """
    return len(list(genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME like '" + tl_collection + "%' AND META_DATA_ATTR_NAME = 'dataset_id' "
        "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
        genquery.AS_LIST, ctx
    )))

#    return count + len(list(genquery.row_iterator(
#        "DATA_ID",
#        "COLL_NAME = '" + tl_collection + "' AND META_DATA_ATTR_NAME = 'dataset_id' "
#        "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
#        genquery.AS_LIST, ctx
#    )))


def get_aggregated_object_error_count(ctx, dataset_id, tl_collection):
    """ return total amounts of object errors """
    return len(list(genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME like '" + tl_collection + "%' AND META_DATA_ATTR_NAME = 'error' ",
        genquery.AS_LIST, ctx
    )))

#    return count + len(list(genquery.row_iterator(
#        "DATA_ID",
#        "COLL_NAME = '" + tl_collection + "' AND META_DATA_ATTR_NAME = 'error' ",
#        genquery.AS_LIST, ctx
#    )))


def get_aggregated_object_warning_count(ctx, dataset_id, tl_collection):
    """ return total amounts of object warnings """
    return len(list(genquery.row_iterator(
        "DATA_ID",
        "COLL_NAME like '" + tl_collection + "%' AND META_DATA_ATTR_NAME = 'warning' ",
        genquery.AS_LIST, ctx
    )))

#    return count + len(list(genquery.row_iterator(
#        "DATA_ID",
#        "COLL_NAME = '" + tl_collection + "' AND META_DATA_ATTR_NAME = 'warning' ",
#        genquery.AS_LIST, ctx
#    )))


def dataset_make_id(scope):
    """ Construct a dateset based on WEPV and directory """
    return scope['wave'] + '\t' + scope['experiment_type'] + '\t' + scope['pseudocode'] + '\t' + scope['version'] + '\t' + scope['directory']


def dataset_parse_id(dataset_id):
    """ Parse a dataset into its consructive data """
    dataset_parts = dataset_id.split('\t')
    dataset = {}
    dataset['wave'] = dataset_parts[0]
    dataset['experiment_type'] = dataset_parts[1]  ## IS DIT NOG ERGENS GOED VOOR
    dataset['expType'] = dataset_parts[1]
    dataset['pseudocode'] = dataset_parts[2]
    dataset['version'] = dataset_parts[3]
    dataset['directory'] = dataset_parts[4] # HIER WORDT NIKS MEE GEDAAN - toch ff zo laten

    return dataset

