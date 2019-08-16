# \file      iiMetadata.py
# \brief     JSON metadata handling
# \author    Chris Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import jsonschema


def iiSaveFormMetadata(rule_args, callback, rei):
    """Validate and store JSON metadata for a given collection"""

    # For now, JSON schema "required" errors are always ignored.

    coll, metadata_text = rule_args

    def report(x):
        """ XXX Temporary, for debugging """
        callback.writeString("serverLog", x)
        callback.writeString("stdout", x)

    try:
        schema = getSchema(callback, coll)
    except UUException as e:
        report(json.dumps({'status': 'Error',
                           'statusInfo': 'Could not load metadata schema'}))
        return

    # Load form metadata input.
    try:
        metadata = json.loads(metadata_text)
    except ValueError as e:
        # NB: python3 raises json.JSONDecodeError instead.
        # This should only happen if the form was tampered with.
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'JSON decode error'}))
        return

    def transform_error(e):
        """ Turn a ValidationError into a data structure for the frontend """
        return {'message': e.message,
                'path': list(e.path),
                'schema_path': list(e.path),
                'validator': e.validator}

    # Perform validation and filter errors.

    validator = jsonschema.Draft7Validator(schema)

    errors = map(transform_error,
                 # Filter out 'required' errors, to allow saving WIP forms.
                 filter(lambda e: e.validator != 'required',
                        validator.iter_errors(metadata)))

    if len(errors) > 0:
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'Metadata validation failed',
                           'errors':     errors}))
        return

    # No errors: write out JSON.
    try:
        write_data_object(callback, '{}/{}'.format(coll, IIJSONMETADATA),
                          json.dumps(metadata))
    except UUException as e:
        report(json.dumps({'status': 'Error',
                           'statusInfo': 'Could not save yoda-metadata.json'}))
        return

    report(json.dumps({'status': 'Success', 'statusInfo': ''}))

def iiValidateMetadata(rule_args, callback, rei):
    """Validate JSON metadata for a given collection"""

    coll = rule_args[0]

    # Retrieve metadata schema for collection.
    try:
        schema = getSchema(callback, coll)
    except UUException as e:
        rule_args[1] = "1"
        return

    # Load JSON metadata.
    try:
        metadata_text = read_data_object(callback, '{}/{}'.format(coll, IIJSONMETADATA))
        metadata = json.loads(metadata_text)
    except UUException as e:
        rule_args[1] = "1"
        return

    # Perform validation.
    validator = jsonschema.Draft7Validator(schema)

    if validator.is_valid(metadata):
        rule_args[1] = "0"
    else:
        rule_args[1] = "1"

    return
