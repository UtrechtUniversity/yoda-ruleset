"""JSON metadata handling."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import re
from collections import OrderedDict
from datetime import datetime
from typing import List

import genquery
import irods_types
from tstrings import t

import provenance
import publication
import schema as schema_
import vault
from metadata_utils import get_json_metadata_errors, humanize_validation_error, is_json_metadata_valid
from util import *

__all__ = ['rule_meta_validate',
           'api_meta_remove',
           'api_meta_clone_file',
           'rule_meta_modified_post',
           'rule_meta_datamanager_vault_ingest',
           'rule_meta_collection_has_cloneable_metadata',
           'rule_get_latest_vault_metadata_path']


def metadata_get_links(metadata: dict) -> List:
    if 'links' not in metadata or type(metadata['links']) is not list:
        return []
    return list(filter(lambda x: type(x) in (dict, OrderedDict)
                       and 'rel' in x
                       and 'href' in x
                       and type(x['rel']) is str
                       and type(x['href']) is str,
                       metadata['links']))


def metadata_get_schema_id(metadata: dict) -> str | None:
    desc = list(filter(lambda x: x['rel'] == 'describedby', metadata_get_links(metadata)))
    if len(desc) > 0:
        return desc[0]['href']
    return None


def metadata_set_schema_id(metadata: dict, schema_id: str) -> None:
    other_links = list(filter(lambda x: x['rel'] != 'describedby', metadata_get_links(metadata)))

    metadata['links'] = [OrderedDict([
        ['rel',  'describedby'],
        ['href', schema_id]
    ])] + other_links


def get_collection_metadata_path(ctx: rule.Context, coll: str) -> str | None:
    """Check if a collection has a JSON metadata file and provide its path, if any.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of collection to check for metadata

    :returns: Path to metadata file
    """
    path = f'{coll}/{constants.IIJSONMETADATA}'
    if data_object.exists(ctx, path):
        return path

    return None


def get_latest_vault_metadata_path(ctx: rule.Context, vault_pkg_coll: str) -> str | None:
    """Get the latest vault metadata JSON file.

    :param ctx:            Combined type of a callback and rei struct
    :param vault_pkg_coll: Vault package collection

    :returns: Metadata JSON path
    """
    name = None

    iter = genquery.row_iterator(
        "DATA_NAME",
        t("COLL_NAME = '{vault_pkg_coll}' AND DATA_NAME like 'yoda-metadata[%].json'"),
        genquery.AS_LIST, ctx)

    for row in iter:
        data_name = row[0]
        if name is None or (name < data_name and len(name) <= len(data_name)):
            name = data_name

    return None if name is None else f'{vault_pkg_coll}/{name}'


rule_get_latest_vault_metadata_path = (
    rule.make(inputs=[0], outputs=[1],
              transform=lambda x: x if type(x) is str else '')
             (get_latest_vault_metadata_path))


def rule_meta_validate(rule_args, callback, rei):
    """Validate JSON metadata file."""
    json_path = rule_args[0]

    try:
        errs = get_json_metadata_errors(callback, json_path)
    except error.UUError as e:
        errs = [{'message': str(e)}]

    if len(errs):
        rule_args[1] = '1'
        rule_args[2] = 'metadata validation failed:\n' + '\n'.join([err['message'] for err in errs])
    else:
        rule_args[1] = '0'
        rule_args[2] = 'metadata validated'


def collection_has_cloneable_metadata(ctx: rule.Context, coll: str) -> str | None:
    """Check if a collection has metadata, and validate it.

    This always ignores 'required' schema attributes, since metadata can
    only be cloned in the research area.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of collection to check for cloneable metadata

    :returns: String with the parent metadata_path on success or None otherwise.
    """
    path = get_collection_metadata_path(ctx, coll)

    if path is None:
        return None

    if path.endswith('.json'):
        if is_json_metadata_valid(ctx, path, ignore_required=True):
            return path

    return None


rule_meta_collection_has_cloneable_metadata = (
    rule.make(inputs=[0], outputs=[1],
              transform=lambda x: x if type(x) is str else '')
             (collection_has_cloneable_metadata))


@api.make()
def api_meta_remove(ctx: rule.Context, coll: str) -> None:
    """Remove a collection's metadata JSON, if it exists."""
    log.write(ctx, f'Remove metadata of coll {coll}')

    try:
        data_object.remove(ctx, f'{coll}/{constants.IIJSONMETADATA}')
    except error.UUError:
        # ignore non-existent files.
        # (this may also fail for other reasons, but we can't distinguish them)
        pass


@api.make()
def api_meta_clone_file(ctx: rule.Context, target_coll: str) -> api.Result:
    """Clone a metadata file from a parent collection to a subcollection.

    :param ctx:         Combined type of a callback and rei struct
    :param target_coll: Target collection (where the metadata is copied to)

    :returns: API result
    """
    source_coll = pathutil.chop(target_coll)[0]  # = parent collection
    source_data = get_collection_metadata_path(ctx, source_coll)

    if source_data and source_data.endswith('.json'):
        target_data = f'{target_coll}/{constants.IIJSONMETADATA}'
    else:
        return api.Error('no_metadata', 'No metadata file exists to clone')

    try:
        data_object.copy(ctx, source_data, target_data)
    except msi.Error as e:
        return api.Error('copy_failed', 'The metadata file could not be copied', str(e))


# Functions that deal with ingesting metadata into AVUs {{{

def ingest_metadata_research(ctx: rule.Context, path: str) -> None:
    """Validate JSON metadata (without requiredness) and ingests as AVUs in the research space."""
    coll, data = pathutil.chop(path)

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, f'ingest_metadata_research failed: Could not read {path} as JSON')
        return

    if not is_json_metadata_valid(ctx, path, metadata, ignore_required=True):
        log.write(ctx, f'ingest_metadata_research failed: {path} is invalid')
        return

    # Note: We do not set a $id in research space: this would trigger jsonavu
    # validation, which does not respect our wish to ignore required
    # properties in the research area.

    # Replace all metadata under this namespace.
    jsonutil.set_on_object(ctx, coll, "collection",
                           constants.UUUSERMETADATAROOT,
                           jsonutil.dump(metadata))


def ingest_metadata_deposit(ctx: rule.Context, path: str) -> None:
    """Validate JSON metadata (without requiredness) and ingests as AVUs in the deposit space."""
    coll, data = pathutil.chop(path)

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, f'ingest_metadata_deposit failed: Could not read {path} as JSON')
        return

    if not is_json_metadata_valid(ctx, path, metadata, ignore_required=True):
        log.write(ctx, f'ingest_metadata_deposit failed: {path} is invalid')
        return

    # Set Title and Data Access Restriction of deposit as AVU.
    if 'Title' in metadata:
        avu.associate_to_coll(ctx, coll, 'Title', metadata['Title'])
    if 'Data_Access_Restriction' in metadata:
        avu.associate_to_coll(ctx, coll, 'Data_Access_Restriction', metadata['Data_Access_Restriction'])


def ingest_metadata_staging(ctx: rule.Context, path: str) -> None:
    """Set cronjob metadata flag and triggers vault ingest."""
    avu.set_on_data(ctx, path, f"{constants.UUORGMETADATAPREFIX}cronjob_vault_ingest", constants.CRONJOB_STATE['PENDING'])

    # Note: Validation is triggered via ExecCmd in rule_meta_datamanager_vault_ingest.
    #
    # msiExecCmd is currently not usable from Python rule engine:
    # https://github.com/irods/irods_rule_engine_plugin_python/issues/11
    # msi.exec_cmd(ctx, "admin-vaultingest.sh", user.full_name(ctx), "", "", "", irods_types.ExecCmdOut())
    ctx.iiAdminVaultIngest()


def update_index_metadata(ctx: rule.Context, path: str, metadata: dict, creation_time: str, data_package: str) -> None:
    """Update the index attributes for JSON metadata."""
    msi.coll_create(ctx, path, "", irods_types.BytesBuf())
    avu.rmw_from_coll(ctx, '%', '%', constants.UUFLATINDEX)
    avu_op = "add"
    avu_unit = constants.UUFLATINDEX
    metadata_operations = {
        "entity_name": path,
        "entity_type": "collection",
        "operations": []
    }

    for creator in metadata['Creator']:
        name = creator['Name']
        if 'Given_Name' in name and 'Family_Name' in name:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Creator",
                "value": name['Given_Name'] + ' ' + name['Family_Name'],
                "units": avu_unit
            })
        if 'Owner_Role' in creator:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Owner_Role",
                "value": creator['Owner_Role'],
                "units": avu_unit
            })

    if 'Contributor' in metadata:
        for contributor in metadata['Contributor']:
            if 'Name' in contributor:
                name = contributor['Name']
                if 'Given_Name' in name and 'Family_Name' in name:
                    metadata_operations['operations'].append({
                        "operation": avu_op,
                        "attribute": "Contributor",
                        "value": name['Given_Name'] + ' ' + name['Family_Name'],
                        "units": avu_unit
                    })

    if 'Tag' in metadata:
        for tag in metadata['Tag']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Tag",
                "value": tag,
                "units": avu_unit
            })

    extend_operations = [
        {
            "operation": avu_op,
            "attribute": "Title",
            "value": metadata['Title'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Description",
            "value": metadata['Description'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Data_Access_Restriction",
            "value": metadata['Data_Access_Restriction'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Creation_Time",
            "value": creation_time,
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Creation_Year",
            "value": str(datetime.fromtimestamp(int(creation_time)).year),
            "units": avu_unit
        }]

    metadata_operations['operations'].extend(extend_operations)

    if 'Research_Group' in metadata:
        metadata_operations['operations'].append({
            "operation": avu_op,
            "attribute": "Research_Group",
            "value": metadata['Research_Group'],
            "units": avu_unit
        })
    if 'Collection_Name' in metadata:
        metadata_operations['operations'].append({
            "operation": avu_op,
            "attribute": "Collection_Name",
            "value": metadata['Collection_Name'],
            "units": avu_unit
        })
    if 'Collected' in metadata:
        if 'Start_Date' in metadata['Collected']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Collected_Start_Year",
                "value": metadata['Collected']['Start_Date'][:4],
                "units": avu_unit
            })
        if 'End_Date' in metadata['Collected']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Collected_End_Year",
                "value": metadata['Collected']['End_Date'][:4],
                "units": avu_unit
            })

    if 'GeoLocation' in metadata:
        for geoLocation in metadata['GeoLocation']:
            if 'Description_Spatial' in geoLocation:
                metadata_operations['operations'].append({
                    "operation": avu_op,
                    "attribute": "Description_Spatial",
                    "value": geoLocation['Description_Spatial'],
                    "units": avu_unit
                })

    if config.enable_data_package_reference:
        metadata_operations['operations'].append({
            "operation": "add",
            "attribute": "Data_Package_Reference",
            "value": data_package,
            "units": avu_unit
        })

    if avu.apply_atomic_operations(ctx, metadata_operations):
        log.write(ctx, f'update_index_metadata: Metadata index update successful on path {path}')
    else:
        log.write(ctx, f'update_index_metadata: Metadata index update unsuccessful on path {path}')


def ingest_metadata_vault(ctx: rule.Context, path: str) -> None:
    """Ingest (pre-validated) JSON metadata in the vault."""
    # The JSON metadata file has just landed in the vault, required validation /
    # logging / provenance has already taken place.

    # Read the metadata file and apply it as AVUs.

    coll = pathutil.chop(path)[0]

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, f'ingest_metadata_vault failed: Could not read {path} as JSON')
        return

    # Get creation time.
    creation_time = ""
    iter = genquery.row_iterator(
        "COLL_CREATE_TIME",
        t("COLL_NAME = '{coll}'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        creation_time = str(int(row[0]))

    # Get Data Package Reference.
    data_package = ""
    if config.enable_data_package_reference:
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.DATA_PACKAGE_REFERENCE}'"),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            data_package = row[0]

    # Update flat index metadata for OpenSearch.
    if config.enable_open_search and group.exists(ctx, coll.split("/")[3].replace("vault-", "deposit-", 1)):
        update_index_metadata(ctx, coll + "/index", metadata, creation_time, data_package)

    # Replace all metadata under this namespace.
    jsonutil.set_on_object(ctx, coll, "collection",
                           constants.UUUSERMETADATAROOT,
                           jsonutil.dump(metadata))

# }}}


@rule.make()
def rule_meta_modified_post(ctx: rule.Context, path: str, user: str, zone: str) -> None:
    if re.match(f'^/{zone}/home/datamanager-[^/]+/vault-[^/]+/.*', path):
        ingest_metadata_staging(ctx, path)
    elif re.match(f'^/{zone}/home/vault-[^/]+/.*', path):
        ingest_metadata_vault(ctx, path)
        vault.update_archive(ctx, path)
    elif re.match(f'^/{zone}/home/research-[^/]+/.*', path):
        ingest_metadata_research(ctx, path)
    elif re.match(f'^/{zone}/home/deposit-[^/]+/.*', path):
        ingest_metadata_deposit(ctx, path)


def rule_meta_datamanager_vault_ingest(rule_args, callback, rei):
    """Ingest changes to metadata into the vault."""
    # This rule is called via ExecCmd during a policy rule
    # (ingest_metadata_staging), with as an argument the path to a metadata
    # JSON in a staging area (a location in a datamanager home collection).
    #
    # As user rods, we validate the metadata, and if successful, copy it, timestamped, into the vault.
    # Necessary log & provenance info is recorded, and a publication update is triggered if necessary.
    # An AVU update is triggered via policy during the copy action.
    ctx = rule.Context(callback, rei)
    json_path = rule_args[0]
    rule_args[1:3] = 'UnknownError', ''

    # FIXME: this kvp issue needs to be addressed on a wider scale.
    if json_path.find('++++') != -1:
        return

    def set_result(msg_short, msg_long):
        rule_args[1:3] = msg_short, msg_long
        if msg_short != 'Success':
            log.write(ctx, f'rule_meta_datamanager_vault_ingest failed: {msg_long}')
        return

    # Parse path to JSON object.
    m = re.match(f'^/([^/]+)/home/(datamanager-[^/]+)/(vault-[^/]+)/(.+)/{constants.IIJSONMETADATA}$', json_path)
    if not m:
        set_result('JsonPathInvalid', f'Json staging path <{json_path}> invalid')
        return

    zone, dm_group, vault_group, vault_subpath = m.groups()
    dm_path = f'/{zone}/home/{dm_group}'

    # Make sure the vault package coll exists.
    vault_path = f'/{zone}/home/{vault_group}'
    vault_pkg_path = f'{vault_path}/{vault_subpath}'

    if not collection.exists(ctx, vault_pkg_path):
        set_result('JsonPathInvalid', f'Vault path <{vault_pkg_path}> does not exist')
        return

    actor = data_object.owner(ctx, json_path)
    if actor is None:
        set_result('JsonPathInvalid', f'Json object <{json_path}> does not exist')
        return
    actor = actor[0]  # Discard zone name.

    # Make sure rods has access to the json file.
    client_full_name = user.full_name(ctx)

    # Get the metadata before the ingest
    previous_metadata = get_latest_vault_metadata_path(ctx, vault_pkg_path)
    prev_json = jsonutil.read(ctx, previous_metadata)
    prev_json_data = json.loads(json.dumps(prev_json))

    try:
        ret = msi.check_access(ctx, json_path, 'modify_object', irods_types.BytesBuf())
        if ret['arguments'][2] != b'\x01':
            msi.set_acl(ctx, 'default', 'admin:own', client_full_name, json_path)
    except error.UUError:
        set_result('AccessError', 'Couldn\'t grant access to json metadata file')
        return

    # Determine destination filename.
    # FIXME - TOCTOU: should do this in a loop around msi.data_obj_copy instead.
    ret = msi.get_icat_time(ctx, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    json_name, json_ext = constants.IIJSONMETADATA.split('.', 1)
    dest = f'{vault_pkg_path}/{json_name}[{timestamp}].{json_ext}'
    i = 0
    while data_object.exists(ctx, dest):
        i += 1
        dest = f'{vault_pkg_path}/{json_name}[{timestamp}][{i}].{json_ext}'

    # Validate metadata.
    # FIXME - TOCTOU: might fix by reading JSON only once, and validating and writing to vault from that.
    ret = callback.rule_meta_validate(json_path, '', '')
    invalid = ret['arguments'][1]
    if invalid == '1':
        set_result('FailedToValidateJSON', ret['arguments'][2])
        return

    # Copy the file, with its ACLs.
    try:
        # Note: This copy triggers metadata/AVU ingestion via policy.
        msi.data_obj_copy(ctx, json_path, dest, f'destRescName={config.resource_vault}++++verifyChksum=', irods_types.BytesBuf())
    except error.UUError:
        set_result('FailedToCopyJSON', f'Couldn\'t copy json metadata file from <{json_path}> to <{dest}>')
        return

    # Get the metadata after the ingest
    latest_metadata = get_latest_vault_metadata_path(ctx, vault_pkg_path)
    current_json = jsonutil.read(ctx, latest_metadata)
    current_json_data = json.loads(json.dumps(current_json))

    try:
        vault.copy_acls_from_parent(ctx, dest, "default")
    except Exception:
        set_result('FailedToSetACLs', f'Failed to set vault permissions on <{dest}>')
        return

    # Log the difference between the metadata before and after the ingest
    difference_descriptions = diff_data.describe_metadata_changes(prev_json_data, current_json_data)
    for description in difference_descriptions:
        provenance.log_action(ctx, actor, vault_pkg_path, description)

    # Write license file.
    vault.vault_write_license(ctx, vault_pkg_path)

    # Cleanup staging area.
    try:
        data_object.remove(ctx, json_path, force=True)
    except Exception:
        set_result('FailedToRemoveDatamanagerMetadata', f'Failed to remove <{json_path}>')
        return

    stage_coll = f'/{zone}/home/{dm_group}/{vault_group}'
    if collection.is_empty(ctx, stage_coll):
        try:
            # We may or may not have delete access already.
            msi.set_acl(ctx, 'recursive', 'admin:own', client_full_name, dm_path)
        except error.UUError:
            pass
        try:
            msi.rm_coll(ctx, stage_coll, 'forceFlag=', irods_types.BytesBuf())
        except error.UUError:
            set_result('FailedToRemoveColl', f'Failed to remove <{stage_coll}>')
            return

    # Update publication if package is published.
    status = vault.get_coll_vault_status(ctx, vault_pkg_path)
    if status is constants.vault_package_state.PUBLISHED:
        # Add publication update status to vault package.
        # Also used in frontend to check if vault package metadata update is pending.
        try:
            avu.set_on_coll(ctx, vault_pkg_path, f"{constants.UUORGMETADATAPREFIX}cronjob_publication_update", constants.CRONJOB_STATE['PENDING'])
            publication.set_update_publication_state(ctx, vault_pkg_path)
        except Exception:
            set_result('FailedToSetPublicationUpdateStatus',
                       f'Failed to set publication update status on <{vault_pkg_path}>')
            return

    set_result('Success', '')


def copy_user_metadata(ctx: rule.Context, source: str, target: str) -> None:
    """Copy the user metadata (AVUs) of a collection to another collection.

    This only copies user metadata, so it ignores system metadata.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    try:
        # Retrieve all AVUs inside source collection.
        user_metadata = list(avu.inside_coll(ctx, source, recursive=True))

        # Group AVUs by entity and filter system metadata.
        grouped_user_metadata: dict = {}
        for path, type, attribute, value, unit in user_metadata:
            if not attribute.startswith(constants.UUORGMETADATAPREFIX) and unit != constants.UUFLATINDEX and not unit.startswith(constants.UUUSERMETADATAROOT + '_'):
                grouped_user_metadata.setdefault(path, {"type": type, "avus": []})
                grouped_user_metadata[path]["avus"].append((attribute, value, unit))

        # Generate metadata operations.
        for path, item in grouped_user_metadata.items():
            operations = {
                "entity_name": path.replace(source, f"{target}/original", 1),
                "entity_type": item["type"],
                "operations": []
            }

            for attribute, value, unit in item["avus"]:
                operations["operations"].append(
                    {
                        "operation": "add",
                        "attribute": attribute,
                        "value": value,
                        "units": unit
                    }
                )

            # Apply metadata operations.
            if not avu.apply_atomic_operations(ctx, operations):
                log.write(ctx, f"copy_user_metadata: failed to copy user metadata for <{path}>")

        log.write(ctx, f"copy_user_metadata: copied user metadata from <{source}> to <{target}/original>")
    except Exception:
        log.write(ctx, f"copy_user_metadata: failed to copy user metadata from <{source}> to <{target}/original>")


def vault_metadata_matches_schema(ctx: rule.Context, coll_name: str, schema_cache: dict, report_name: str, write_stdout: bool) -> dict | None:
    """Process a single data package to retrieve and validate that its metadata conforms to the schema.

    :param ctx:          Combined type of a callback and rei struct
    :param coll_name:    String representing the data package collection path.
    :param schema_cache: Dictionary storing schema blueprints, can be empty.
    :param report_name:  Name of report script (for logging)
    :param write_stdout: A boolean representing whether to write to stdout or rodsLog

    :returns: A dictionary result containing if schema matches and the schema short name.
    """
    metadata_path = get_latest_vault_metadata_path(ctx, coll_name)

    if not metadata_path:
        log.write(ctx, f"{report_name} skips {coll_name}, because metadata could not be found.", write_stdout)
        return None

    try:
        metadata = jsonutil.read(ctx, metadata_path)
    except Exception as exc:
        log.write(ctx, f"{report_name} skips {coll_name}, because of exception while reading metadata file {metadata_path}: {str(exc)}", write_stdout)
        log.write(ctx, f"vault_metadata_matches_schema: Error while reading metadata file {metadata_path} of data package {coll_name}: {str(exc)}", write_stdout)
        return None

    # Determine schema
    schema_id = schema_.get_schema_id(ctx, metadata_path)
    if schema_id is None:
        return None

    schema_shortname = schema_id.split("/")[-2]

    # Retrieve schema and cache it for future use
    schema_path = schema_.get_schema_path_by_id(ctx, metadata_path, schema_id)
    if schema_shortname in schema_cache:
        schema_contents = schema_cache[schema_shortname]
    else:
        schema_contents = jsonutil.read(ctx, schema_path)
        schema_cache[schema_shortname] = schema_contents

    # Check whether metadata matches schema and log any errors
    error_list = get_json_metadata_errors(ctx, metadata_path, metadata=metadata, schema=schema_contents)
    match_schema = len(error_list) == 0
    if not match_schema:
        errors_formatted = [humanize_validation_error(e).encode('utf-8') for e in error_list]
        log.write(ctx, f"{report_name}: metadata {metadata_path} did not match schema {schema_shortname}: {str(errors_formatted)}", write_stdout)
        log.write(ctx, f"vault_metadata_matches_schema: Metadata {metadata_path} of data package {coll_name} did not match the schema {schema_shortname}. Error list: {str(errors_formatted)}", write_stdout)

    return {"schema": schema_shortname, "match_schema": match_schema}
