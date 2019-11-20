# -*- coding: utf-8 -*-
"""JSON metadata handling."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
import json
import jsonschema
import jsonavu
import irods_types

from enum import Enum
from collections import OrderedDict

from util import *
import schema as schema_

__all__ = ['rule_uu_meta_validate',
           'api_uu_meta_remove',
           'api_uu_meta_clone_file',
           'rule_uu_meta_modified_post',
           'rule_uu_meta_datamanager_vault_ingest',
           'rule_uu_meta_collection_has_cloneable_metadata']


def metadata_get_links(metadata):
    if 'links' not in metadata or type(metadata['links']) is not list:
        return []
    return filter(lambda x: type(x) in (dict, OrderedDict)
                            and 'rel'  in x
                            and 'href' in x
                            and type(x['rel'])  is str
                            and type(x['href']) is str,
                  metadata['links'])


def metadata_get_schema_id(metadata):
    desc = filter(lambda x: x['rel'] == 'describedby', metadata_get_links(metadata))
    if len(desc) > 0:
        return desc[0]['href']


def metadata_set_schema_id(metadata, schema_id):
    other_links = filter(lambda x: x['rel'] != 'describedby', metadata_get_links(metadata))

    metadata['links'] = [OrderedDict([
        ['rel',  'describedby'],
        ['href', schema_id]
    ])] + other_links


def get_json_metadata_errors(callback,
                             metadata_path,
                             metadata=None,
                             schema=None,
                             ignore_required=False):
    """Validate JSON metadata, and return a list of errors, if any.
       The path to the JSON object must be provided, so that the active schema path
       can be derived. Optionally, a pre-parsed JSON object may be provided in
       'metadata'.

       The checked schema is, by default, the active schema for the given metadata path,
       however it can be overridden by providing a parsed JSON schema as an argument.

       This will throw exceptions on missing metadata / schema files and invalid
       JSON formats.
    """

    if schema is None:
        schema = schema_.get_active_schema(callback, metadata_path)

    if metadata is None:
        metadata = jsonutil.read(callback, metadata_path)

    # Perform validation and filter errors.
    validator = jsonschema.Draft7Validator(schema)

    errors = validator.iter_errors(metadata)

    if ignore_required:
        errors = filter(lambda e: e.validator not in ['required', 'dependencies'], errors)

    def transform_error(e):
        """Turn a ValidationError into a data structure for the frontend"""
        return {'message':     e.message,
                'path':        list(e.path),
                'schema_path': list(e.schema_path),
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
    except error.UUError as e:
        # File may be missing or not valid JSON.
        return False


def get_collection_metadata_path(callback, coll):
    """Check if a collection has a metadata file and provide its path, if any.
       Both JSON and legacy XML are checked, JSON has precedence if it exists.
    """

    for path in ['{}/{}'.format(coll, x) for x in [constants.IIJSONMETADATA,
                                                   constants.IIMETADATAXMLNAME]]:
        if data_object.exists(callback, path):
            return path

    return None


def get_latest_vault_metadata_path(callback, vault_pkg_coll):
    """Get the latest vault metadata JSON file.

       :param vault_pkg_coll: Vault package collection

       :returns: string -- Metadata JSON path
    """
    name = None

    iter = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME = '{}' AND DATA_NAME like 'yoda-metadata[%].json'".format(vault_pkg_coll),
        genquery.AS_LIST, callback)

    for row in iter:
        data_name = row[0]
        if name is None or (name < data_name and len(name) <= len(data_name)):
            name = data_name

    return None if name is None else '{}/{}'.format(vault_pkg_coll, name)


def rule_uu_meta_validate(rule_args, callback, rei):
    """Validate JSON metadata file"""

    json_path = rule_args[0]

    try:
        errs = get_json_metadata_errors(callback, json_path)
    except error.UUError as e:
        errs = {'message': str(e)}

    if len(errs):
        rule_args[1] = '1'
        rule_args[2] = 'metadata validation failed:\n' + '\n'.join([e['message'] for e in errs])
    else:
        rule_args[1] = '0'
        rule_args[2] = 'metadata validated'


def collection_has_cloneable_metadata(callback, coll):
    """Check if a collection has metadata, and validate it.
       Returns the parent metadata_path on success, or False otherwise.

       This always ignores 'required' schema attributes, since metadata can
       only be cloned in the research area.
    """
    path = get_collection_metadata_path(callback, coll)

    if path is None:
        return False

    if path.endswith('.json'):
        if is_json_metadata_valid(callback, path, ignore_required=True):
            return path

    return False


rule_uu_meta_collection_has_cloneable_metadata = (
    rule.make(inputs=[0], outputs=[1],
              transform=lambda x: x if type(x) is str else '')
             (collection_has_cloneable_metadata))


@api.make()
def api_uu_meta_remove(ctx, coll):
    """Remove a collection's metadata JSON and XML, if they exist"""

    log.write(ctx, 'Remove metadata of coll {}'.format(coll))

    for path in ['{}/{}'.format(coll, x) for x in [constants.IIJSONMETADATA,
                                                   constants.IIMETADATAXMLNAME]]:
        try:
            data_object.remove(ctx, path)
        except error.UUError as e:
            # ignore non-existent files.
            # (this may also fail for other reasons, but we can't distinguish them)
            pass


@api.make()
def api_uu_meta_clone_file(ctx, target_coll):
    """Clones a metadata file from a parent collection to a subcollection.
       The destination collection (where the metadata is copied *to*) is given as an argument.
    """

    source_coll = pathutil.chop(target_coll)[0]  # = parent collection
    source_data = get_collection_metadata_path(ctx, source_coll)

    if source_data is None:
        # No metadata to clone? Abort.
        return
    elif source_data.endswith('.json'):
        target_data = '{}/{}'.format(target_coll, constants.IIJSONMETADATA)
    else:
        # XML metadata files must be transformed to JSON before cloning.
        return

    try:
        msi.data_obj_copy(ctx, source_data, target_data, '', irods_types.BytesBuf())
    except msi.Error as e:
        raise api.Error('copy_failed', 'The metadata file could not be copied', str(e))


# Functions that deal with ingesting metadata into AVUs {{{

def ingest_metadata_research(ctx, path):
    """Validates JSON metadata (without requiredness) and ingests as AVUs in the research space."""

    coll, data = pathutil.chop(path)

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError as e:
        log.write(ctx, 'ingest_metadata_research failed: Could not read {} as JSON'.format(path))
        return

    if not is_json_metadata_valid(ctx, path, metadata, ignore_required=True):
        log.write(ctx, 'ingest_metadata_research failed: {} is invalid'.format(path))
        return

    # Remove any remaining legacy XML-style AVUs.
    ctx.iiRemoveAVUs(coll, constants.UUUSERMETADATAPREFIX)

    # Note: We do not set a $id in research space: this would trigger jsonavu
    # validation, which does not respect our wish to ignore required
    # properties in the research area.

    # Replace all metadata under this namespace.
    ctx.setJsonToObj(coll, '-C',
                     constants.UUUSERMETADATAROOT,
                     jsonutil.dump(metadata))


def ingest_metadata_staging(ctx, path):
    """Sets cronjob metadata flag and triggers vault ingest."""

    coll = pathutil.chop(path)[0]

    ret = string_2_key_val_pair(ctx,
                                '{}{}{}'.format(constants.UUORGMETADATAPREFIX,
                                                'cronjob_vault_ingest=',
                                                CRONJOB_STATE['PENDING']),
                                irods_types.BytesBuf())

    set_key_value_pairs_to_obj(ctx, ret['arguments'][1], path, '-d')

    # Note: Validation is triggered via ExecCmd in rule_uu_meta_datamanager_vault_ingest.
    ctx.iiAdminVaultIngest()


def ingest_metadata_vault(ctx, path):
    """Ingest (pre-validated) JSON metadata in the vault."""

    # The JSON metadata file has just landed in the vault, required validation /
    # logging / provenance has already taken place.

    # Read the metadata file and apply it as AVUs.

    coll = pathutil.chop(path)[0]

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError as e:
        log.write(ctx, 'ingest_metadata_vault failed: Could not read {} as JSON'.format(path))
        return

    # Remove any remaining legacy XML-style AVUs.
    ctx.iiRemoveAVUs(coll, constants.UUUSERMETADATAPREFIX)

    # Replace all metadata under this namespace.
    ctx.setJsonToObj(coll, '-C',
                     constants.UUUSERMETADATAROOT,
                     jsonutil.dump(metadata))

# }}}


@rule.make()
def rule_uu_meta_modified_post(ctx, path, user, zone):

    if re.match('^/{}/home/datamanager-[^/]+/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_staging(ctx, path)
    elif re.match('^/{}/home/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_vault(ctx, path)
    elif re.match('^/{}/home/research-[^/]+/.*'.format(zone), path):
        ingest_metadata_research(ctx, path)


def rule_uu_meta_datamanager_vault_ingest(rule_args, callback, rei):
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
            log.write(callback, 'rule_uu_meta_datamanager_vault_ingest failed: {}'.format(msg_long))
        return

    # Parse path to JSON object.
    m = re.match('^/([^/]+)/home/(datamanager-[^/]+)/(vault-[^/]+)/(.+)/{}$'.format(constants.IIJSONMETADATA), json_path)
    if not m:
        set_result('JsonPathInvalid', 'Json staging path <{}> invalid'.format(json_path))
        return

    zone, dm_group, vault_group, vault_subpath = m.groups()
    dm_path = '/{}/home/{}'.format(zone, dm_group)

    # Make sure the vault package coll exists.
    vault_path = '/{}/home/{}'.format(zone, vault_group)
    vault_pkg_path = '{}/{}'.format(vault_path, vault_subpath)

    if not collection.exists(callback, vault_pkg_path):
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
    except error.UUError as e:
        set_result('AccessError', 'Couldn\'t grant access to json metadata file')
        return

    # Determine destination filename.
    # FIXME - TOCTOU: also exists in XML version
    #      -> should do this in a loop around msi.data_obj_copy instead.
    ret = get_icat_time(callback, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    json_name, json_ext = constants.IIJSONMETADATA.split('.', 1)
    dest = '{}/{}[{}].{}'.format(vault_pkg_path, json_name, timestamp, json_ext)
    i = 0
    while data_object.exists(callback, dest):
        i += 1
        dest = '{}/{}[{}][{}].{}'.format(vault_pkg_path, json_name, timestamp, i, json_ext)

    # Validate metadata.
    # FIXME - TOCTOU: also exists in XML version
    #      -> might fix by reading JSON only once, and validating and writing to vault from that.
    ret = callback.rule_uu_meta_validate(json_path, '', '')
    invalid = ret['arguments'][1]
    if invalid == '1':
        set_result('FailedToValidateJSON', ret['arguments'][2])
        return

    # Copy the file, with its ACLs.
    try:
        # Note: This copy triggers metadata/AVU ingestion via policy.
        msi.data_obj_copy(callback, json_path, dest, 'verifyChksum=', irods_types.BytesBuf())
    except error.UUError as e:
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
    callback.rule_uu_vault_write_provenance_log(vault_pkg_path)

    # Cleanup staging area.
    try:
        data_object.remove(callback, json_path)
    except Exception as e:
        set_result('FailedToRemoveDatamanagerXML', 'Failed to remove <{}>'.format(json_path))
        return

    stage_coll = '/{}/home/{}/{}'.format(zone, dm_group, vault_group)
    if collection_empty(callback, stage_coll):
        try:
            # We may or may not have delete access already.
            set_acl(callback, 'recursive', 'admin:own', client_full_name, dm_path)
        except error.UUError as e:
            pass
        try:
            rm_coll(callback, stage_coll, 'forceFlag=', irods_types.BytesBuf())
        except error.UUError as e:
            set_result('FailedToRemoveColl', 'Failed to remove <{}>'.format(stage_coll))
            return

    # Update publication if package is published.
    ret = callback.iiVaultStatus(vault_pkg_path, '')
    status = ret['arguments'][1]
    if status == constants.VAULT_PACKAGE_STATE['PUBLISHED']:
        # Add publication update status to vault package.
        # Also used in frontend to check if vault package metadata update is pending.
        s = constants.UUORGMETADATAPREFIX + "cronjob_publication_update=" + CRONJOB_STATE['PENDING']
        try:
            ret = string_2_key_val_pair(callback, s, irods_types.BytesBuf())
            kvp = ret['arguments'][1]
            associate_key_value_pairs_to_obj(callback, kvp, vault_pkg_path, '-C')

            callback.iiSetUpdatePublicationState(vault_pkg_path, irods_types.BytesBuf())
        except Exception:
            set_result('FailedToSetPublicationUpdateStatus',
                       'Failed to set publication update status on <{}>'.format(vault_pkg_path))
            return

    set_result('Success', '')
