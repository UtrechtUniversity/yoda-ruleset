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
