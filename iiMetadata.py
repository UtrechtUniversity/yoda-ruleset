# \file      iiMetadata.py
# \brief     JSON metadata handling
# \author    Chris Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import re
import json
import jsonschema
import jsonavu


def get_json_metadata_errors(callback,
                             metadata_path,
                             metadata = None,
                             ignore_required = False):
    """Validate JSON metadata, and return a list of errors, if any.
       The path to the JSON object must be provided, so that the schema path can be derived.
       Optionally, a pre-parsed JSON object may be provided in 'metadata'.

       Will throw exceptions on missing metadata / schema files and invalid JSON formats.
    """

    schema = getSchema(callback, metadata_path)

    if metadata is None:
        metadata = read_json_object(callback, metadata_path)

    # Perform validation and filter errors.

    validator = jsonschema.Draft7Validator(schema)

    errors = validator.iter_errors(metadata)

    if ignore_required:
        errors = filter(lambda e: e.validator != 'required', errors)

    def transform_error(e):
        """Turn a ValidationError into a data structure for the frontend"""
        return {'message':     e.message,
                'path':        list(e.path),
                'schema_path': list(e.path),
                'validator':   e.validator}

    return map(transform_error, errors)


def is_json_metadata_valid(callback,
                           metadata_path,
                           metadata = None,
                           ignore_required = False):
    """Check if json metadata contains no errors.
       argument 'metadata' may contain a preparsed JSON document, otherwise it
       is loaded from the provided path.
    """

    try:
        return len(get_json_metadata_errors(callback,
                                            metadata_path,
                                            metadata        = metadata,
                                            ignore_required = ignore_required)) == 0
    except UUException as e:
        # File may be missing or not valid JSON.
        return False


def get_collection_metadata_path(callback, coll):
    """Check if a collection has a metadata file and provide its path, if any.
       Both JSON and legacy XML are checked, JSON has precedence if it exists.
    """

    for path in ['{}/{}'.format(coll, x) for x in [IIJSONMETADATA, IIMETADATAXMLNAME]]:
        if data_object_exists(callback, path):
            return path

    return None


def iiSaveFormMetadata(rule_args, callback, rei):
    """Validate and store JSON metadata for a given collection"""

    # For now, JSON schema "required" errors are always ignored.

    coll, metadata_text = rule_args[0:2]

    def report(x):
        """ XXX Temporary, for debugging """
        callback.writeString("serverLog", x)
        callback.writeString("stdout", x)

    # Load form metadata input.
    try:
        metadata = parse_json(metadata_text)
    except UUException as e:
        # This should only happen if the form was tampered with.
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'JSON decode error'}))
        return

    errors = get_json_metadata_errors(callback, coll, metadata, ignore_required = True)

    if len(errors) > 0:
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'Metadata validation failed',
                           'errors':     errors}))
        return

    # No errors: write out JSON.
    try:
        write_data_object(callback, '{}/{}'.format(coll, IIJSONMETADATA),
                          json.dumps(metadata, indent = 4))
    except UUException as e:
        report(json.dumps({'status': 'Error',
                           'statusInfo': 'Could not save yoda-metadata.json'}))
        return

    report(json.dumps({'status': 'Success', 'statusInfo': ''}))


def iiValidateMetadata(rule_args, callback, rei):
    """Validate JSON metadata file for a given collection"""

    coll = rule_args[0]

    if is_json_metadata_valid(callback, '{}/{}'.format(coll, IIJSONMETADATA)):
        rule_args[1] = "0"
    else:
        rule_args[1] = "1"


def iiCollectionHasCloneableMetadata(rule_args, callback, rei):
    """Check if a collection has metadata, and validate it.
       Returns ('true', metadata_path) on success.

       This always ignores 'required' schema attributes, since metadata can
       only be cloned in the research area.
    """

    coll = rule_args[0]
    path = get_collection_metadata_path(callback, coll)

    rule_args[1:3] = ('false', '')

    if path is None:
        return

    elif path.endswith('.json'):
        if is_json_metadata_valid(callback, path, ignore_required = True):
            rule_args[1:3] = ('true', path)

    elif path.endswith('.xml'):
        # Run XML validator instead.
        ret = callback.iiGetResearchXsdPath(path, '')
        xsd_path = ret['arguments'][1]
        ret = callback.iiValidateXml(path, xsd_path, '', '')
        invalid, msg = ret['arguments'][2:4]
        if invalid != b'\x01':
            rule_args[1:3] = ('true', path)


def iiRemoveAllMetadata(rule_args, callback, rei):
    """Remove a collection's metadata JSON and XML, if they exist"""

    coll = rule_args[0]

    for path in ['{}/{}'.format(coll, x) for x in [IIJSONMETADATA, IIMETADATAXMLNAME]]:
        try:
            data_obj_unlink(callback,
                            'objPath={}++++forceFlag='.format(path),
                            irods_types.BytesBuf())
        except UUMsiException as e:
            # ignore non-existent files.
            pass


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


def iiMetadataJsonModifiedPost(rule_args, callback, rei):

    path, user, zone = rule_args[0:4]

    if re.match('^/{}/home/datamanager-[^/]+/vault-[^/]+/.*/{}$'
                    .format(zone, IIJSONMETADATA), path):
        # Vault metadata?
        # Set cronjob metadata flag and trigger vault ingest.

        set_key_value_pairs_to_obj(callback, ret['arguments'][1], path, '-d')

        ret = string_2_key_val_pair(callback,
                                    '{}{}{}'.format(UUORGMETADATAPREFIX,
                                                    'cronjob_vault_ingest=',
                                                    CRONJOB_STATE['PENDING']),
                                    irods_types.BytesBuf())

        set_key_value_pairs_to_obj(callback, ret['arguments'][1], path, '-d')

        callback.iiAdminVaultIngest()

    else:
        # Research metadata: update AVUs
        coll, data = chop_path(path)
        callback.writeString('serverLog',
                             'iiMetadataJsonModifiedPost: {} added to {}. Importing metadata\n'
                             .format(data, coll))

        try:
            metadata = read_json_object(callback, path)
        except UUException as e:
            callback.writeString('serverLog',
                                 'iiMetadataJsonModifiedPost failed: Could not read {} as JSON\n'
                                 .format(path))
            return

        if not is_json_metadata_valid(callback, path, metadata, ignore_required = True):
            callback.writeString('serverLog',
                                 'iiMetadataJsonModifiedPost failed: {} is invalid\n'
                                 .format(path))
            return

        # Remove any remaining legacy XML-style AVUs.
        callback.iiRemoveAVUs(coll, UUUSERMETADATAPREFIX)

        # Note: We do not set a schema $id in research space: this would trigger jsonavu
        # validation, which does not respect our wish to ignore required
        # properties in the research area.

        # Replace all metadata under this namespace.
        callback.setJsonToObj(coll, '-C',
                              UUUSERMETADATAROOT,
                              json.dumps(metadata))
