# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with JSON."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from collections import OrderedDict

import jsonavu

import avu
import data_object
import error
import log
import msi


class ParseError(error.UUError):
    """Exception for unparsable JSON text."""


def parse(text):
    """Parse JSON into an OrderedDict.

    :param text:       JSON to parse into an OrderedDict

    :raises ParseError: JSON file format error

    :returns: JSON string as OrderedDict
    """
    try:
        return json.loads(text, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError:
        raise ParseError('JSON file format error')


def dump(data, **options):
    """Dump an object to a JSON string."""
    # json.dumps seems to not like mixed str/unicode input, so make sure
    # everything is of the same type first.
    return json.dumps(data,
                      ensure_ascii=False,  # Don't unnecessarily use \u0000 escapes.
                      **({'indent': 4} if options == {} else options))


def read(callback, path, **options):
    """Read an iRODS data object and parse it as JSON."""
    return parse(data_object.read(callback, path), **options)


def write(callback, path, data, **options):
    """Write a JSON object to an iRODS data object."""
    return data_object.write(callback, path, dump(data, **options))


def set_on_object(ctx, path, type, namespace, json_string):
    """Write a JSON object as AVUs to an iRODS object.

    :param ctx:         Combined type of a callback and rei struct
    :param path:        Path of object
    :param type:        Type of object ('data_object' or 'collection')
    :param namespace:   Namespace of AVUs
    :param json_string: JSON string to write as AVUs

    :returns: Boolean indicating if all metadata operations were executed
    """
    data = json.loads(json_string)

    # Remove existing metadata from object in namespace.
    msi_type = "-d"
    if type == "collection":
        msi_type = "-C"
    try:
        msi.rmw_avu(ctx, msi_type, path, "%", "%", "{}_%".format(namespace))
    except msi.Error as e:
        # Ignore -819000 (CAT_SUCCESS_BUT_WITH_NO_INFO) errors when removing metadata.
        if str(e).find("-819000") > -1:
            log.write(ctx, "set_on_object: no metadata to remove")
        else:
            return False

    # Convert JSON data to AVUs.
    avus = jsonavu.json2avu(data, namespace)

    # Generate metadata operations.
    operations = {
        "entity_name": path,
        "entity_type": type,
        "operations": []
    }

    for item in avus:
        operations["operations"].append(
            {
                "operation": "add",
                "attribute": item["a"],
                "value": item["v"],
                "units": item["u"]
            }
        )

    # Apply metadata operations.
    return avu.apply_atomic_operations(ctx, operations)
