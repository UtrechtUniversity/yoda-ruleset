"""Functions for handling schema updates within any yoda-metadata file."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2018-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_transform_vault_metadata',
           'rule_batch_vault_metadata_correct_orcid_format',
           'rule_batch_vault_metadata_schema_report',
           'rule_get_transformation_info',
           'api_transform_metadata']

import json
import os
import re
import time
from typing import Callable, Dict, Tuple

import genquery

import meta
import schema
import schema_transformations
from util import *


def execute_transformation(ctx: rule.Context, metadata_path: str, transform: Callable, keep_metadata_backup: bool = True) -> None:
    """Transform a metadata file with the given transformation function."""
    coll, data = os.path.split(metadata_path)

    group_name = metadata_path.split('/')[3]

    metadata = jsonutil.read(ctx, metadata_path)
    metadata = transform(ctx, metadata)

    # make_metadata_backup is only relevant for research
    if group_name.startswith('research-'):
        if keep_metadata_backup:
            backup = '{}/transformation-backup[{}].json'.format(coll, str(int(time.time())))
            data_object.copy(ctx, metadata_path, backup)
        jsonutil.write(ctx, metadata_path, metadata)
    elif group_name.startswith('vault-'):
        new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
        jsonutil.write(ctx, new_path, metadata)
        copy_acls_from_parent(ctx, new_path, "default")
        ctx.rule_provenance_log_action("system", coll, "updated metadata schema")
        log.write(ctx, "Transformed %s" % (new_path))
    else:
        raise AssertionError()


@api.make()
def api_transform_metadata(ctx: rule.Context, coll: str, keep_metadata_backup: bool = True) -> api.Result:
    """Transform a yoda-metadata file in the given collection to the active schema."""
    metadata_path = meta.get_collection_metadata_path(ctx, coll)
    if metadata_path and metadata_path.endswith('.json'):
        # JSON metadata.
        log.write(ctx, 'Transforming JSON metadata in the research space: <{}>'.format(metadata_path))
        transform = get(ctx, metadata_path)

        if transform is None:
            return api.Error('undefined_transformation', 'No transformation found')

        execute_transformation(ctx, metadata_path, transform, keep_metadata_backup)
    else:
        return api.Error('no_metadata', 'No metadata file found')


def get(ctx: rule.Context, metadata_path: str, metadata: Dict | None = None) -> Callable | None:
    """Find a transformation that can be executed on the given metadata JSON.

    :param ctx:           Combined type of a ctx and rei struct
    :param metadata_path: Path to metadata JSON
    :param metadata:      Optional metadata object

    :returns: Transformation function on success, or None if no transformation was found
    """
    try:
        src = schema.get_schema_id(ctx, metadata_path, metadata=metadata)
        dst = schema.get_active_schema_id(ctx, metadata_path)

        # Ideally, we would check that the metadata is valid in its current
        # schema before claiming that we can transform it...
        # print('{} -> {}'.format(src,dst))
        if src is None:
            return None

        return schema_transformations.get(src, dst)
    except KeyError:
        return None
    except error.UUError:
        # print('{} -> {} ERR {}'.format(src,dst, e))
        return None


@rule.make(inputs=[0], outputs=[1, 2])
def rule_get_transformation_info(ctx: rule.Context, json_path: str) -> Tuple[str, str]:
    """Check if a yoda-metadata.json transformation is possible and if so, retrieve transformation description.

    :param ctx:            Combined type of a ctx and rei struct
    :param json_path:      metadata JSON path

    :returns:              Tuple that consists of two elements:
                           [1] Transformation possible? true|false
                           [2] human-readable description of the transformation

    """
    output: Tuple[str, str]  = ('false', '')

    transform = get(ctx, json_path)

    if transform is not None:
        output = ('true', html(transform))

    return output


def copy_acls_from_parent(ctx: rule.Context, path: str, recursive_flag: str) -> None:
    """
    When inheritance is missing we need to copy ACLs when introducing new data in vault package.

    :param ctx:            Combined type of a ctx and rei struct
    :param path:           Path of object that needs the permissions of parent
    :param recursive_flag: Either "default" for no recursion or "recursive"
    """
    parent = os.path.dirname(path)

    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        access_name = row[0]
        user_id = int(row[1])

        user_name = user.name_from_id(ctx, user_id)

        # iRODS keeps ACLs for deleted users in the iCAT database (https://github.com/irods/irods/issues/7778),
        # so we need to skip ACLs referring to users that no longer exist.
        if user_name == "":
            continue

        if access_name == "own":
            log.write(ctx, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "own", user_name, path)
        elif access_name == "read_object":
            log.write(ctx, "iiCopyACLsFromParent: granting read to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "read", user_name, path)
        elif access_name == "modify_object":
            log.write(ctx, "iiCopyACLsFromParent: granting write to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "write", user_name, path)


@rule.make(inputs=[0, 1, 2, 3], outputs=[])
def rule_batch_transform_vault_metadata(ctx: rule.Context, coll_id_s: str, batch_s: str, pause_s: str, delay_s: str) -> None:
    """
    Transform all metadata JSON files in the vault to the active schema.

    :param ctx:            Combined type of a ctx and rei struct
    :param coll_id_s:      First COLL_ID to check - initial = 0
    :param batch_s:        Batch size, <= 256
    :param pause_s:        Pause between checks (float)
    :param delay_s:        Delay between batches in seconds
    """
    coll_id = int(coll_id_s)
    batch   = int(batch_s)
    pause   = float(pause_s)
    delay   = int(delay_s)

    # Check one batch of metadata schemas.

    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_NAME like 'yoda-metadata%%json' AND COLL_ID >= '%d'" % (user.zone(ctx), coll_id),
        genquery.AS_LIST, ctx)

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        path_parts = coll_name.split('/')

        # Only process collections that are directly beneath the apex
        # vault collection, e.g. /zoneName/home/vault-foo/data-package[123],
        # since metadata in the original part of the data package should not
        # be processed.
        if not re.match(r"^\/[^\/]+\/home\/[^\/]+\/[^\/]+$", coll_name):
            continue

        try:
            # Get vault package path.
            vault_package = '/'.join(path_parts[:5])
            metadata_path = meta.get_latest_vault_metadata_path(ctx, vault_package)
            log.write(ctx, "[METADATA] Checking whether metadata needs to be transformed: " + metadata_path)
            if metadata_path != '':
                transform = get(ctx, metadata_path)
                if transform is not None:
                    log.write(ctx, "[METADATA] Executing transformation for: " + metadata_path)
                    execute_transformation(ctx, metadata_path, transform)
        except Exception as e:
            log.write(ctx, "[METADATA] Exception occurred during schema transformation of {}: {}".format(coll_name, str(type(e)) + ":" + str(e)))

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id += 1
    else:
        # All done.
        coll_id = 0
        log.write(ctx, "[METADATA] Finished updating metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        ctx.delayExec(
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_transform_vault_metadata('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


@rule.make(inputs=[0, 1, 2, 3, 4], outputs=[])
def rule_batch_vault_metadata_correct_orcid_format(ctx: rule.Context, coll_id_s: str, batch_s: str, pause_s: str, delay_s: str, dryrun_s: str) -> None:
    """
    Correct ORCID person identifier with invalid format in metadata JSON files in the vault.

    :param ctx:            Combined type of a ctx and rei struct
    :param coll_id_s:      First COLL_ID to check - initial = 0
    :param batch_s:        Batch size, <= 256
    :param pause_s:        Pause between checks (float)
    :param delay_s:        Delay between batches in seconds
    :param dryrun_s:       Dry-run mode ('true' or 'false'; everything else is considered 'false')
    """

    coll_id = int(coll_id_s)
    batch   = int(batch_s)
    pause   = float(pause_s)
    delay   = int(delay_s)
    dryrun_mode = dryrun_s == "true"

    # Check one batch of metadata schemas.

    # Find all vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND COLL_NAME not like '%%/original' AND DATA_NAME like 'yoda-metadata%%json' AND COLL_ID >= '%d'" % (user.zone(ctx), coll_id),
        genquery.AS_LIST, ctx)

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        path_parts = coll_name.split('/')

        try:
            # Get vault package path.
            vault_package = '/'.join(path_parts[:5])
            metadata_path = meta.get_latest_vault_metadata_path(ctx, vault_package)
            if metadata_path is not None:
                metadata = jsonutil.read(ctx, metadata_path)

                # We only need to transform metadata with schemas that do not constrain ORCID format
                license_url = metadata.get("links", {})[0].get("href", "")
                license = license_url.replace("https://yoda.uu.nl/schemas/", "").replace("/metadata.json", "")
                if license not in ['core-1', 'core-2', 'default-1', 'default-2', 'default-3', 'hptlab-1', 'teclab-1', 'dag-0', 'vollmer-0']:
                    log.write(ctx, "Skipping data package '%s' for ORCID transformation because license '%s' is excluded."
                              % (vault_package, license))
                    continue

                # Correct the incorrect orcid(s) if possible
                # result is a dict containing 'data_changed' 'metadata'
                result = transform_orcid(ctx, metadata)

                # In order to minimize changes within the vault only save a new metadata.json if there actually has been at least one orcid correction.
                if result['data_changed'] and not dryrun_mode:
                    # orcid('s) has/have been adjusted. Save the changes in the same manner as execute_transformation for vault packages.
                    coll, data = os.path.split(metadata_path)
                    new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
                    log.write(ctx, 'TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
                    jsonutil.write(ctx, new_path, result['metadata'])
                    copy_acls_from_parent(ctx, new_path, "default")
                    ctx.rule_provenance_log_action("system", coll, "updated person identifier metadata")
                    log.write(ctx, "Transformed ORCIDs for: %s" % (new_path))
                elif result['data_changed']:
                    log.write(ctx, "Would have transformed ORCIDs for: %s if dry run mode was disabled." % (metadata_path))

        except Exception as e:
            log.write(ctx, "Exception occurred during ORCID transformation of {}: {}".format(coll_name, str(type(e)) + ":" + str(e)))

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id += 1
    else:
        # All done.
        coll_id = 0
        log.write(ctx, "[METADATA] Finished correcting ORCID's within vault metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        ctx.delayExec(
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_vault_metadata_correct_orcid_format('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


def transform_orcid(ctx: rule.Context, m: Dict) -> Dict:
    """
    Transform all present orcid's into the correct format. If possible!

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform

    :returns: Dict with indication whether data has changed and transformed JSON object with regard to ORCID
    """
    data_changed = False

    # Only Creators and Contributors hold Person identifiers that can hold ORCIDs.
    for pi_holder in ['Creator', 'Contributor']:
        if m.get(pi_holder, False):
            for holder in m[pi_holder]:
                for pi in holder.get('Person_Identifier', dict()):
                    if pi.get('Name_Identifier_Scheme', None)  == 'ORCID':
                        # If incorrect ORCID format => try to correct.
                        if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", pi.get('Name_Identifier', None)):
                            original_orcid = pi['Name_Identifier']
                            corrected_orcid = correctify_orcid(original_orcid)
                            # Only it an actual correction took place change the value and mark this data as 'changed'.
                            if corrected_orcid is None:
                                log.write(ctx, "Warning: unable to automatically fix ORCID '%s'" % (original_orcid))
                            elif corrected_orcid != original_orcid:
                                log.write(ctx, "Updating ORCID '{}' to '{}'".format(original_orcid, corrected_orcid))
                                pi['Name_Identifier'] = corrected_orcid
                                data_changed = True

    return {'metadata': m, 'data_changed': data_changed}


def correctify_orcid(org_orcid: str) -> str | None:
    """Function to correct illformatted ORCIDs. Returns None if value cannot be fixed."""
    # Get rid of all spaces.
    orcid = org_orcid.replace(' ', '')

    # Upper-case X.
    orcid = org_orcid.replace('x', 'X')

    # The last part should hold a valid id like eg: 1234-1234-1234-123X.
    # If not, it is impossible to correct it to the valid orcid format
    orcs = orcid.split('/')
    if not re.search("^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcs[-1]):
        return None

    return "https://orcid.org/{}".format(orcs[-1])


def html(f: Callable) -> str:
    """Get a human-readable HTML description of a transformation function.

    The text is derived from the function's docstring.

    :param f: Transformation function

    :returns: Human-readable HTML description of a transformation function
    """
    docstring = "" if f.__doc__ is None else f.__doc__
    description = '\n'.join(map(lambda paragraph:
                            '<p>{}</p>'.format(  # Trim whitespace.
                                re.sub(r'\s+', ' ', paragraph).strip()),
                                # Docstring paragraphs are separated by blank lines.
                                re.split('\n{2,}', docstring)))

    # Remove docstring.
    return re.sub('((:param).*)|((:returns:).*)', ' ', description)


@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_metadata_schema_report(ctx: rule.Context) -> str:
    """Show vault metadata schema about each data package in vault

    :param ctx:      Combined type of a callback and rei struct

    :returns:        JSON-encoded dictionary, where each key is a vault data package path.
                     Values are dictionaries with keys "schema" (contains the short name of the schema
                     (e.g. 'default-3', as per the information in the metadata file, or empty if no metadata
                     schema could be found), and match_schema (contains a boolean value that indicates whether
                     the metadata matches the JSON schema). match_schema only has a meaning if a metadata schema
                     could be found.
    """
    results = {}
    schema_cache = {}

    # Find all vault collections
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND COLL_NAME not like '%%/original' AND COLL_NAME NOT LIKE '%%/original/%%' AND DATA_NAME like 'yoda-metadata%%json'" %
        (user.zone(ctx)),
        genquery.AS_LIST, ctx)

    for row in iter:
        try:
            coll_name = row[0]
            result = meta.vault_metadata_matches_schema(ctx, coll_name, schema_cache, "Vault metadata schema report", True)
            if result:
                results[coll_name] = result
        except Exception as e:
            log.write(ctx, "Error processing collection {}: {}".format(coll_name, str(e)))
            continue

    return json.dumps(results)
