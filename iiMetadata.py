# \file      iiMetadata.py
# \brief     JSON metadata handling
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import jsonschema

def iiSaveFormMetadata(rule_args, callback, rei):
    """Validate and store JSON metadata for a given collection"""

    # For now, JSON schema "required" errors are always ignored.

    coll, metadata_text = rule_args

    schema = getSchema(callback, coll)

    def report(x):
        """ XXX Temporary, for debugging """
        callback.writeString("serverLog", x)
        callback.writeString("stdout", x)

    # Load form metadata input.
    try:
        metadata = json.loads(metadata_text)
    except JSONDecodeError as e:
        # Should only happen if the form was tampered with.
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
                           'errors':     errors }))
        return

    # No errors: write out JSON.

    # TODO: Use a constant for json filename.

    writeFile(callback, '{}/{}'.format(coll, 'metadata.json'), json.dumps(metadata))

    report(json.dumps({'status': 'Success', 'statusInfo': ''}))
