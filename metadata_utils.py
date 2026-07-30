"""Utility functions for metadata management."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
import sys
from typing import Dict, List, Union

import jsonschema

from util import error, rule

if 'unittest' not in sys.modules:
    import schema as schema_
    from util import jsonutil


def get_json_metadata_errors(ctx: rule.Context,
                             metadata_path: str,
                             metadata: Union[Dict, None] = None,
                             schema: Union[Dict, None] = None,
                             ignore_required: bool = False) -> List:
    """
    Validate JSON metadata, and return a list of errors, if any.

    The path to the JSON object must be provided, so that the active schema path
    can be derived. Optionally, a pre-parsed JSON object may be provided in
    'metadata'.

    The checked schema is, by default, the active schema for the given metadata path,
    however it can be overridden by providing a parsed JSON schema as an argument.

    This will throw exceptions on missing metadata / schema files and invalid
    JSON formats.

    :param ctx:             Combined type of a callback and rei struct
    :param metadata_path:   Path to the JSON object
    :param metadata:        Pre-parsed JSON object
    :param schema:          Schema to check against
    :param ignore_required: Ignore required fields

    :returns: List of errors in JSON object
    """
    def transform_error(e):
        """Turn a ValidationError into a data structure for the frontend."""
        return {'message':     e.message,
                'path':        list(e.path),
                'schema_path': list(e.schema_path),
                'validator':   e.validator}

    if schema is None:
        schema = schema_.get_active_schema(ctx, metadata_path)

    if metadata is None:
        metadata = jsonutil.read(ctx, metadata_path)

    # Perform validation and filter errors.
    validator = jsonschema.Draft201909Validator(schema)
    errors = list(validator.iter_errors(metadata))

    if ignore_required:
        errors = list(filter(lambda e: e.validator not in ['required', 'dependencies'], errors))

    return list(map(transform_error, errors))


def is_json_metadata_valid(ctx: rule.Context,
                           metadata_path: str,
                           metadata: Union[Dict, None] = None,
                           ignore_required: bool = False) -> bool:
    """Check if json metadata contains no errors.

    Argument 'metadata' may contain a preparsed JSON document, otherwise it
    is loaded from the provided path.

    :param ctx:             Combined type of a callback and rei struct
    :param metadata_path:   Path to the JSON object
    :param metadata:        Pre-parsed JSON object
    :param ignore_required: Ignore required fields

    :returns: Boolean indicating if JSON metadata is valid
    """
    try:
        return len(get_json_metadata_errors(ctx,
                                            metadata_path,
                                            metadata=metadata,
                                            ignore_required=ignore_required)) == 0
    except error.UUError:
        # File may be missing or not valid JSON.
        return False


def humanize_validation_error(e: dict) -> str:
    """Transform a jsonschema validation error such that it is readable by humans.

    :param e: a dictionary containing ValidationError data. The get_json_metadata_errors
              function returns a list of dictionaries in the expected format.

    :returns: a supposedly human-readable description of the error
    """
    # Error format: "Creator 1 -> Person Identifier 1 -> Name Identifier Scheme"

    # Make array indices human-readable.
    path_out = []
    for _i, x in enumerate(e['path']):
        if isinstance(x, int):
            path_out[-1] = '{} {}'.format(path_out[-1], x + 1)
        else:
            path_out += [x.replace('_', ' ')]

    # Get the names of disallowed extra fields.
    # (the jsonschema library isn't of much help here - we must extract it from the message)
    if e['validator'] in ['additionalProperties', 'unevaluatedProperties'] and len(path_out) == 0:
        m_single = re.search(r'[\'\"]([^\"\']+)[\'\"] was unexpected', e['message'])
        m_multiple = re.search(r'\((([\'\"]([^\"\']+)[\'\"], )+([\'\"]([^\"\']+)[\'\"])) were unexpected\)', e['message'])
        if m_single:
            return 'This extra field is not allowed: ' + m_single.group(1)
        elif m_multiple:
            return 'These extra fields are not allowed: ' + m_multiple.group(1)
        else:
            return 'Extra fields are not allowed'
    elif e['validator'] == 'required':
        m = re.search("[\'\"]([^\"\']+)[\'\"] is a required property", e['message'])
        if m:
            return 'This field is missing: ' + m.group(1)
        else:
            return 'There are missing fields'
    elif len(path_out) > 0:
        return 'This field contains an error: ' + ' -> '.join(path_out)
    else:
        # If we don't have a standard message or at least a specific path,
        # fall back to the message returned by the validator.
        return 'Validation error: ' + e['message']
