# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with JSON."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from collections import OrderedDict

import data_object
import error


class ParseError(error.UUError):
    """
    Exception for unparsable JSON text.

    Python2's JSON lib raises ValueError on bad parses, which is ambiguous.
    Use this exception (together with the functions below) instead.
    (this can also ease transitions to python3, since python3's json already
    uses a different, unambiguous exception type: json.JSONDecodeError)
    """


def _fold(x, **alg):
    """Fold over a JSON structure.

    Calls functions from 'alg', indexed by the type of value, to transform values recursively.

    :param x:     JSON structure
    :param **alg: Functions to fold over JSON structure

    :returns: Function f folded over a JSON structure
    """
    f = alg.get(type(x).__name__, lambda y: y)
    if type(x) in [dict, OrderedDict]:
        return f(OrderedDict([(k, _fold(v, **alg)) for k, v in x.items()]))
    elif type(x) is list:
        return f([_fold(v, **alg) for v in x])
    else:
        return f(x)


def _demote_strings(json_data):
    """Transform unicode -> UTF-8 encoded strings recursively, for a given JSON structure.

    Needed for handling unicode in JSON as long as we are still using Python2.
    Both JSON string values and JSON object (dict) keys are transformed.

    :param json_data: JSON structure to transform

    :returns: JSON structure with unicode strings transformed to UTF-8 encoded strings
    """
    return _fold(json_data,
                 unicode=lambda x: x.encode('utf-8'),
                 OrderedDict=lambda x: OrderedDict([(k.encode('utf-8'), v) for k, v in x.items()]))


def _promote_strings(json_data):
    """Transform UTF-8 encoded strings -> unicode recursively, for a given JSON structure.

    Needed for handling unicode in JSON as long as we are still using Python2.
    Both JSON string values and JSON object (dict) keys are transformed.

    May raise UnicodeDecodeError if strings are not proper UTF-8.

    :param json_data: JSON structure to transform

    :returns: JSON structure with UTF-8 encoded strings transformed to unicode strings
    """
    return _fold(json_data,
                 str=lambda x: x.decode('utf-8'),
                 OrderedDict=lambda x: OrderedDict([(k.decode('utf-8'), v) for k, v in x.items()]),
                 dict=lambda x: OrderedDict([(k.decode('utf-8'), v) for k, v in x.items()]))


def parse(text, want_bytes=True):
    """Parse JSON into an OrderedDict.

    :param text:       JSON to parse into an OrderedDict
    :param want_bytes: Should strings be UTF-8 encoded?

    :raises ParseError: JSON file format error

    :returns: JSON string as OrderedDict
    """
    try:
        x = json.loads(text, object_pairs_hook=OrderedDict)
        return x
    except ValueError:
        raise ParseError('JSON file format error')


def dump(data, **options):
    """Dump an object to a JSON string."""
    return json.dumps(data,
                      ensure_ascii=False,  # Don't unnecessarily use \u0000 escapes.
                      **({'indent': 4} if options == {} else options))


def read(callback, path, **options):
    """Read an iRODS data object and parse it as JSON."""
    return parse(data_object.read(callback, path), **options)


def write(callback, path, data, **options):
    """Write a JSON object to an iRODS data object."""
    return data_object.write(callback, path, dump(data, **options))


def remove_empty(d):
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary"""
    def empty(x):
        return x is None or x == {} or x == []

    if not isinstance(d, (dict, list)):
        return d
    elif isinstance(d, list):
        return [v for v in (remove_empty(v) for v in d) if not empty(v)]
    else:
        return {k: v for k, v in ((k, remove_empty(v)) for k, v in d.items()) if not empty(v)}
