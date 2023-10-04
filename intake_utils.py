# -*- coding: utf-8 -*-

"""Utility functions for the intake module. These are in a separate file so that
   we can test the main logic without having iRODS-related dependencies in the way."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import re


def intake_tokens_identify_dataset(tokens):
    """Check whether the tokens gathered so far are sufficient for identifying a dataset.

    :param tokens: A dictionary of tokens

    :returns: Returns whether a dataset is identified
    """
    required = ['wave', 'experiment_type', 'pseudocode']  # version is optional

    missing = 0
    for req_token in required:
        # required tokens must be present and must have a value
        if req_token not in tokens or tokens[req_token] == "":
            missing = missing + 1

    return (missing == 0)


def intake_ensure_version_present(ctx, metadata):
    """Adds a version attribute with a default value to metadata if it is not yet present.

    :param ctx:           Combined type of a callback and rei struct
    :param metadata:      Dictionary with intake module metadata
    """
    if "version" not in metadata:
        metadata["version"] = "Raw"


def intake_extract_tokens_from_name(ctx, path, scoped_buffer):
    """Extract one or more tokens from a file / directory name and add dataset information as metadata.
    :param ctx:           Combined type of a callback and rei struct
    :param path:          Full path of the data object or collection
    :param scoped_buffer: Holds dataset buffer with prefilled keys
    :returns: Returns extended scope buffer
    """
    basename = os.path.basename(path)
    name_without_ext = os.path.splitext(basename)[0]
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


def intake_scan_get_metadata_update(ctx, path, is_collection, in_dataset, parent_metadata):
    """Determine metadata to be updated for a particular collection or data object, based
       on its name and parent metadata.

       This function is separate from the function that actually performs the updates, so
       that we can test the logic separately.

    :param ctx:    Combined type of a callback and rei struct
    :param path:   Full path of the data object or collection
    :param is_collection: true if it's a collection, false if it's a data object
    :param in_dataset: true if the parent already has complete WEP(V) attributes. Otherwise false.
    :param parent_metadata: dict containing the intake module metadata of the parent collection ( if any)

    :returns: Returns a dictionary with the following keys / values:
        new_metadata: dictionary of new metadata to apply to this data object or collection
        in_dataset: true if current object (along with values passed from parents) has complete WEP(V) values.
                    otherwise false.
    """

    local_metadata = parent_metadata.copy()

    result = {"new_metadata": local_metadata, "in_dataset": in_dataset}

    if in_dataset:
        # If we already are in a dataset, we get all the metadata from the parent. We
        # cannot override attributes in this case. However we need to remove the top-level
        # attribute, because the present object is within in a dataset, and thus not a top-level
        # data object.
        if "dataset_toplevel" in local_metadata:
            del [local_metadata["dataset_toplevel"]]
    else:
        intake_extract_tokens_from_name(ctx, path, local_metadata)
        if intake_tokens_identify_dataset(local_metadata):
            intake_ensure_version_present(ctx, local_metadata)
            local_metadata["directory"] = path if is_collection else os.path.dirname(path)
            local_metadata["dataset_id"] = dataset_make_id(local_metadata)
            local_metadata["dataset_toplevel"] = dataset_make_id(local_metadata)
            result["in_dataset"] = True
        else:
            # result["in_dataset"] is already set to false
            pass

    return result


def dataset_make_id(scope):
    """Construct a dataset based on WEPV and directory.

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
    dataset['experiment_type'] = dataset_parts[1]
    dataset['pseudocode'] = dataset_parts[2]
    dataset['version'] = dataset_parts[3]
    dataset['directory'] = dataset_parts[4]

    return dataset
