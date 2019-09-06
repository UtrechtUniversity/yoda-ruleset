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
                             metadata=None,
                             ignore_required=False):
    """Validate JSON metadata, and return a list of errors, if any.
       The path to the JSON object must be provided, so that the schema path
       can be derived. Optionally, a pre-parsed JSON object may be provided in
       'metadata'.

       Will throw exceptions on missing metadata / schema files and invalid
       JSON formats.
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
                           metadata=None,
                           ignore_required=False):
    """Check if json metadata contains no errors.
       argument 'metadata' may contain a preparsed JSON document, otherwise it
       is loaded from the provided path.
    """

    try:
        return len(get_json_metadata_errors(callback,
                                            metadata_path,
                                            metadata=metadata,
                                            ignore_required=ignore_required)) == 0
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
    """Validate and store JSON metadata for a given collection."""

    def report(x):
        """ XXX Temporary, for debugging """
        callback.writeString("serverLog", x)
        callback.writeString("stdout", x)

    coll, metadata_text = rule_args[0:2]

    # Assume we are in the research area until proven otherwise.
    # (overwritten below in the vault case)
    is_vault = False
    json_path = '{}/{}'.format(coll, IIJSONMETADATA)

    m = re.match('^/([^/]+)/home/(vault-[^/]+)/(.+)$', coll)
    if m:
        # It's a vault path - set up a staging area in the datamanager collection.
        zone, vault_group, vault_subpath = m.groups()

        ret = callback.iiDatamanagerGroupFromVaultGroup(vault_group, '')
        datamanager_group = ret['arguments'][1]
        if datamanager_group == '':
            report(json.dumps({'status':     'InternalError',
                               'statusInfo': 'could not get datamanager group'}))
            return

        tmp_coll = '/{}/home/{}/{}/{}'.format(zone, datamanager_group, vault_group, vault_subpath)

        try:
            coll_create(callback, tmp_coll, '1', irods_types.BytesBuf())
        except UUException as e:
            report(json.dumps({'status':     'FailedToCreateCollection',
                               'statusInfo': 'Failed to create staging area at <{}>'.format(tmp_coll)}))
            return

        # Use staging area instead of trying to write to the vault directly.
        is_vault = True
        json_path = '{}/{}'.format(tmp_coll, IIJSONMETADATA)

    # Load form metadata input.
    try:
        metadata = parse_json(metadata_text)
    except UUException as e:
        # This should only happen if the form was tampered with.
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'JSON decode error'}))
        return

    # Add metadata schema id to JSON.
    schema_id = getSchemaLocation(callback, json_path)
    metadata["$id"] = schema_id

    # Validate JSON metadata.
    errors = get_json_metadata_errors(callback, json_path, metadata, ignore_required=not is_vault)

    if len(errors) > 0:
        report(json.dumps({'status':     'ValidationError',
                           'statusInfo': 'Metadata validation failed',
                           'errors':     errors}))
        return

    # No errors: write out JSON.
    try:
        write_data_object(callback, json_path, json.dumps(metadata, indent=4))
    except UUException as e:
        report(json.dumps({'status': 'Error',
                           'statusInfo': 'Could not save yoda-metadata.json'}))
        return

    report(json.dumps({'status': 'Success', 'statusInfo': ''}))


def iiValidateMetadata(rule_args, callback, rei):
    """Validate JSON metadata file"""

    json_path = rule_args[0]

    try:
        errs = get_json_metadata_errors(callback, json_path)
    except UUException as e:
        errs = {'message': str(e)}

    if len(errs):
        rule_args[1] = '1'
        rule_args[2] = 'metadata validation failed:\n' + '\n'.join([e['message'] for e in errs])
    else:
        rule_args[1] = '0'
        rule_args[2] = 'metadata validated'


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
        if is_json_metadata_valid(callback, path, ignore_required=True):
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
    source_coll = chop_path(target_coll)[0]  # = parent collection

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
        callback.writeString("serverLog", 'Metadata copy from <{}> to <{}> failed: {}'
                             .format(source_data, target_data, e))


# Functions that deal with ingesting metadata into AVU's {{{

def ingest_metadata_research(callback, path):
    """Validates JSON metadata (without requiredness) and ingests as AVUs in the research space."""

    coll, data = chop_path(path)

    try:
        metadata = read_json_object(callback, path)
    except UUException as e:
        callback.writeString('serverLog',
                             'ingest_metadata_research failed: Could not read {} as JSON\n'
                             .format(path))
        return

    if not is_json_metadata_valid(callback, path, metadata, ignore_required=True):
        callback.writeString('serverLog',
                             'ingest_metadata_research failed: {} is invalid\n'
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


def ingest_metadata_staging(callback, path):
    """Sets cronjob metadata flag and triggers vault ingest."""

    coll = chop_path(path)[0]

    ret = string_2_key_val_pair(callback,
                                '{}{}{}'.format(UUORGMETADATAPREFIX,
                                                'cronjob_vault_ingest=',
                                                CRONJOB_STATE['PENDING']),
                                irods_types.BytesBuf())

    set_key_value_pairs_to_obj(callback, ret['arguments'][1], path, '-d')

    # Note: Validation is triggered via ExecCmd in iiIngestDatamanagerMetadataIntoVault.
    callback.iiAdminVaultIngest()


def ingest_metadata_vault(callback, path):
    """Ingest (pre-validated) JSON metadata in the vault."""

    # The JSON metadata file has just landed in the vault, required validation /
    # logging / provenance has already taken place.

    # Read the metadata file and apply it as AVUs.

    coll = chop_path(path)[0]

    try:
        metadata = read_json_object(callback, path)
    except UUException as e:
        callback.writeString('serverLog',
                             'ingest_metadata_vault failed: Could not read {} as JSON\n'
                             .format(path))
        return

    # Remove any remaining legacy XML-style AVUs.
    callback.iiRemoveAVUs(coll, UUUSERMETADATAPREFIX)

    # Replace all metadata under this namespace.
    callback.setJsonToObj(coll, '-C',
                          UUUSERMETADATAROOT,
                          json.dumps(metadata))

# }}}


def iiMetadataJsonModifiedPost(rule_args, callback, rei):

    path, user, zone = rule_args[0:4]

    if re.match('^/{}/home/datamanager-[^/]+/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_staging(callback, path)
    elif re.match('^/{}/home/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_vault(callback, path)
    elif re.match('^/{}/home/research-[^/]+/.*'.format(zone), path):
        ingest_metadata_research(callback, path)


def iiIngestDatamanagerMetadataIntoVault(rule_args, callback, rei):
    """Ingest changes to metadata into the vault."""

    # This rule is called via ExecCmd during a policy rule
    # (ingest_metadata_staging), with as an argument the path to a metadata
    # JSON in a staging area (a location in a datamanager home collection).
    #
    # As user rods, we validate the metadata, and if succesful, copy it, timestamped, into the vault.
    # Necessary log & provenance info is recorded, and a publication update is triggered if necessary.
    # An AVU update is triggered via policy during the copy action.

    json_path = rule_args[0]
    rule_args[1:3] = 'UnknownError', ''

    # FIXME: this kvp issue needs to be addressed on a wider scale.
    if json_path.find('++++') != -1:
        return

    def set_result(msg_short, msg_long):
        rule_args[1:3] = msg_short, msg_long
        if msg_short != 'Success':
            callback.writeString('serverLog', 'iiIngestDatamanagerMetadataIntoVault failed: {}\n'
                                              .format(msg_long))
        return

    # Parse path to JSON object.
    m = re.match('^/([^/]+)/home/(datamanager-[^/]+)/(vault-[^/]+)/(.+)/{}$'.format(IIJSONMETADATA), json_path)
    if not m:
        set_result('JsonPathInvalid', 'Json staging path <{}> invalid'.format(json_path))
        return

    zone, dm_group, vault_group, vault_subpath = m.groups()
    dm_path = '/{}/home/{}'.format(zone, dm_group)

    # Make sure the vault package coll exists.
    vault_path = '/{}/home/{}'.format(zone, vault_group)
    vault_pkg_path = '{}/{}'.format(vault_path, vault_subpath)

    if not collection_exists(callback, vault_pkg_path):
        set_result('JsonPathInvalid', 'Vault path <{}> does not exist'.format(vault_pkg_path))
        return

    actor = data_owner(callback, json_path)
    if actor is None:
        set_result('JsonPathInvalid', 'Json object <{}> does not exist'.format(json_path))
        return
    actor = actor[0]  # Discard zone name.

    # Make sure rods has access to the json file.
    client_full_name = get_client_full_name(rei)

    try:
        ret = check_access(callback, json_path, 'modify object', irods_types.BytesBuf())
        if ret['arguments'][2] != b'\x01':
            set_acl(callback, 'default', 'admin:own', client_full_name, json_path)
    except UUException as e:
        set_result('AccessError', 'Couldn\'t grant access to json metadata file')
        return

    # Determine destination filename.
    # FIXME - TOCTOU: also exists in XML version
    #      -> should do this in a loop around data_obj_copy instead.
    ret = get_icat_time(callback, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    json_name, json_ext = IIJSONMETADATA.split('.', 1)
    dest = '{}/{}[{}].{}'.format(vault_pkg_path, json_name, timestamp, json_ext)
    i = 0
    while data_object_exists(callback, dest):
        i += 1
        dest = '{}/{}[{}][{}].{}'.format(vault_pkg_path, json_name, timestamp, i, json_ext)

    # Validate metadata.
    # FIXME - TOCTOU: also exists in XML version
    #      -> might fix by reading JSON only once, and validating and writing to vault from that.
    ret = callback.iiValidateMetadata(json_path, '', '')
    invalid = ret['arguments'][1]
    if invalid == '1':
        set_result('FailedToValidateJSON', ret['arguments'][2])
        return

    # Copy the file, with its ACLs.
    try:
        # Note: This copy triggers metadata/AVU ingestion via policy.
        data_obj_copy(callback, json_path, dest, 'verifyChksum=', irods_types.BytesBuf())
    except UUException as e:
        set_result('FailedToCopyJSON', 'Couldn\'t copy json metadata file from <{}> to <{}>'
                   .format(json_path, dest))
        return

    try:
        callback.iiCopyACLsFromParent(dest, 'default')
    except Exception as e:
        set_result('FailedToSetACLs', 'Failed to set vault permissions on <{}>'.format(dest))
        return

    # Log actions.
    callback.iiAddActionLogRecord(actor, vault_pkg_path, 'modified metadata')
    callback.iiWriteProvenanceLogToVault(vault_pkg_path)

    # Cleanup staging area.
    try:
        data_obj_unlink(callback, 'objPath={}++++forceFlag='.format(json_path), irods_types.BytesBuf())
    except Exception as e:
        set_result('FailedToRemoveDatamanagerXML', 'Failed to remove <{}>'.format(json_path))
        return

    stage_coll = '/{}/home/{}/{}'.format(zone, dm_group, vault_group)
    if collection_empty(callback, stage_coll):
        try:
            # We may or may not have delete access already.
            set_acl(callback, 'recursive', 'admin:own', client_full_name, dm_path)
        except UUException as e:
            pass
        try:
            rm_coll(callback, stage_coll, 'forceFlag=', irods_types.BytesBuf())
        except UUException as e:
            set_result('FailedToRemoveColl', 'Failed to remove <{}>'.format(stage_coll))
            return

    # Update publication if package is published.
    ret = callback.iiVaultStatus(vault_pkg_path, '')
    status = ret['arguments'][1]
    if status == VAULT_PACKAGE_STATE['PUBLISHED']:
        # Add publication update status to vault package.
        # Also used in frontend to check if vault package metadata update is pending.
        s = UUORGMETADATAPREFIX + "cronjob_publication_update=" + CRONJOB_STATE['PENDING']
        try:
            ret = string_2_key_val_pair(callback, s, irods_types.BytesBuf())
            kvp = ret['arguments'][1]
            associate_key_value_pairs_to_obj(callback, kvp, vault_pkg_path, '-C')

            callback.iiSetUpdatePublicationState(vault_pkg_path, irods_types.BytesBuf())
        except:
            set_result('FailedToSetPublicationUpdateStatus',
                       'Failed to set publication update status on <{}>'.format(vault_pkg_path))
            return

    set_result('Success', '')
