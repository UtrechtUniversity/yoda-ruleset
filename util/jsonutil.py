"""Utility / convenience functions for dealing with JSON."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from collections import OrderedDict

import jsonavu
import orjson
import requests

import avu
import data_object
import error
import log
import msi
import rule


class ParseError(error.UUError):
    """Exception for unparsable JSON text."""


def fast_parse(input: bytes) -> dict:
    """Parse binary JSON data into a dictionary. For most purposes, this
       should be equivalent to the regular parse function, since
       dictionaries preserve order in Python 3.7+. Only the
       specific functions of OrderedDict like move_to_end are
       not available.

    :param input: binary data to parse

    :raises ParseError: JSON file format error

    :returns: JSON data as dictionary
    """
    try:
        return orjson.loads(input)
    except orjson.JSONDecodeError:
        raise ParseError('JSON file format error')


def parse(text: str) -> OrderedDict:
    """Parse JSON into an OrderedDict.

    :param text: JSON to parse into an OrderedDict

    :raises ParseError: JSON file format error

    :returns: JSON string as OrderedDict
    """
    try:
        return json.loads(text, object_pairs_hook=OrderedDict)
    except json.JSONDecodeError:
        raise ParseError('JSON file format error')


def fast_dump(input: dict) -> str:
    """Dump dictionary structure into string data using JSON.
       This is similar to the regular dump function, only it does
       not do any formatting like indenting, and does not support
       options.

    :param input: dictionary data structure

    :returns: JSON data in string format
    """
    return orjson.dumps(input).decode("utf-8")


def dump(data: dict, **options: int) -> str:
    """Dump an object to a JSON string."""
    # json.dumps seems to not like mixed str/unicode input, so make sure
    # everything is of the same type first.
    return json.dumps(data,
                      ensure_ascii=False,  # Don't unnecessarily use \u0000 escapes.
                      **({'indent': 4} if options == {} else options))


def read(ctx: rule.Context, path: str, **options: int) -> OrderedDict:
    """Read an iRODS data object and parse it as JSON."""
    return parse(data_object.read(ctx, path), **options)


def read_from_url(url: str, timeout: int = 10) -> OrderedDict:
    """Read and parse JSON from a remote URL.

    :param url:     The remote URL to read JSON from
    :param timeout: Request timeout in seconds (default: 10)

    :returns: Parsed JSON object
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json(object_pairs_hook=OrderedDict)


def write(ctx: rule.Context, path: str, data: dict, **options: int) -> None:
    """Write a JSON object to an iRODS data object."""
    return data_object.write(ctx, path, dump(data, **options))


def set_on_object(ctx: rule.Context, path: str, type: str, namespace: str, json_string: str) -> bool:
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
    try:
        if type == "collection":
            avu.rmw_from_coll(ctx, path, "%", "%", "{}_%".format(namespace))
        else:
            avu.rmw_from_data(ctx, path, "%", "%", "{}_%".format(namespace))
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
