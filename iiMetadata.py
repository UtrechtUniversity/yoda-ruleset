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

    coll, metadata_text = rule_args[0:2]

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
        metadata = parse_json(metadata_text)
    except UUException as e:
        # This should only happen if the form was tampered with.
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'JSON decode error'}))
        return

    def transform_error(e):
        """Turn a ValidationError into a data structure for the frontend"""
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

def is_json_metadata_valid(callback, metadata_path):
    """Check if a json metadata file is valid"""
    try:
        # Retrieve metadata schema for collection.
        schema = getSchema(callback, metadata_path)

        # Load JSON metadata.
        metadata = read_json_object(callback, metadata_path)

    except UUException as e:
        return False

    validator = jsonschema.Draft7Validator(schema)

    return validator.is_valid(metadata)


def iiValidateMetadata(rule_args, callback, rei):
    """Validate JSON metadata for a given collection"""

    coll = rule_args[0]

    if is_json_metadata_valid(callback, '{}/{}'.format(coll, IIJSONMETADATA)):
        rule_args[1] = "0"
    else:
        rule_args[1] = "1"


def get_collection_metadata_path(callback, coll):
    """Check if a collection has a metadata file and provide its path, if any.
       Both JSON and legacy XML are checked, JSON has precedence if it exists.
    """

    for path in ['{}/{}'.format(coll, x) for x in [IIJSONMETADATA, IIMETADATAXMLNAME]]:
        if data_object_exists(callback, path):
            return path

    return None

def iiCollectionHasMetadata(rule_args, callback, rei):
    """Check if a collection has a metadata file (JSON or XML), returns its path."""

    coll = rule_args[0]
    path = get_collection_metadata_path(callback, coll)

    rule_args[1:3] = ('false', '') if path is None else ('true', path)

def iiCollectionHasValidMetadata(rule_args, callback, rei):
    """Check if a collection has metadata, and validate it.
       Returns ('true', metadata_path) on success.
    """

    coll = rule_args[0]
    path = get_collection_metadata_path(callback, coll)

    rule_args[1:3] = ('false', '')

    if path is None:
        return

    elif path.endswith('.json'):
        if is_json_metadata_valid(callback, path):
            rule_args[1:3] = ('true', path)

    elif path.endswith('.xml'):
        ret = callback.iiGetResearchXsdPath(path, '')
        xsd_path = ret['arguments'][1]
        ret = callback.iiValidateXml(path, xsd_path, '', '')
        invalid, msg = ret['arguments'][2:4]
        if invalid != b'\x01':
            rule_args[1:3] = ('true', path)


def iiCloneMetadataFile(rule_args, callback, rei):
    """Clones a metadata file from a parent collection to a subcollection.
       Both JSON and XML metadata can be copied, JSON takes precedence if it exists.

       The destination collection (where the metadata is copied *to*) is given as an argument.
    """

    target_coll = rule_args[0]
    source_coll = chop_path(target_coll)[0] # = parent collection

    source_data = get_collection_metadata_path(callback, source_coll)

    if source_data is None:
        # No metadata to clone? Abort.
        return
    elif source_data.endswith('.json'):
        target_data = '{}/{}'.format(target_coll, IIJSONMETADATA)
    elif source_data.endswith('.xml'):
        target_data = '{}/{}'.format(target_coll, IIMETADATAXMLNAME)
    else:
        return

    try:
        data_obj_copy(callback, source_data, target_data, '', irods_types.BytesBuf())
    except UUMsiException as e:
        callback.writeString("serverLog",'Metadata copy from <{}> to <{}> failed: {}'
                            .format(source_data, target_data, e))
