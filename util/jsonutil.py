# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with JSON."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import data_object
import error
import json
from collections import OrderedDict


class ParseError(error.UUError):
    """Exception for unparsable JSON text.

    Python2's JSON lib raises ValueError on bad parses, which is ambiguous.
    Use this exception (together with the functions below) instead.
    (this can also ease transitions to python3, since python3's json already
    uses a different, unambiguous exception type: json.JSONDecodeError)
    """


def _fold(x, **alg):
    """Fold over a JSON structure.
    Calls functions from 'alg', indexed by the type of value, to transform values recursively.
    """
    f = alg.get(type(x).__name__, lambda y: y)
    if type(x) is OrderedDict:
        return f(OrderedDict([(k, _fold(v, **alg)) for k, v in x.items()]))
    elif type(x) is list:
        return f([_fold(v, **alg) for v in x])
    else:
        return f(x)


def _demote_strings(json_data):
    """Transform unicode -> UTF-8 encoded strings recursively, for a given JSON structure.
       Needed for handling unicode in JSON as long as we are still using Python2.
       Both JSON string values and JSON object (dict) keys are transformed.
    """
    return _fold(json_data,
                 unicode=lambda x: x.encode('utf-8'),
                 OrderedDict=lambda x: OrderedDict([(k.encode('utf-8'), v) for k, v in x.items()]))


def parse(text):
    """Parse JSON into an OrderedDict. All strings are UTF-8 encoded."""
    try:
        return _demote_strings(json.loads(text, object_pairs_hook=OrderedDict))
    except ValueError:
        raise ParseError('JSON file format error')


def dump(data, **options):
    """Dump an object to a JSON string."""
    return json.dumps(data, **({'indent': 4} if options == {} else options))


def read(callback, path):
    """Read an iRODS data object and parse it as JSON."""
    return parse(data_object.read(callback, path))


def write(callback, path, data, **options):
    """Write a JSON object to an iRODS data object."""
    return data_object.write(callback, path, dump(data, **options))
