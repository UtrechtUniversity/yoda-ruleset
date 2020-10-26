# -*- coding: utf-8 -*-
"""Functions for handling schema updates within any yoda-metadata file."""

__copyright__ = 'Copyright (c) 2018-2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_transform_vault_metadata',
           'rule_get_transformation_info',
           'api_transform_metadata']

import os
import re
import time

import irods_types
import session_vars
import xmltodict

import meta
import schema
import schema_transformations
import vault_xml_to_json
from util import *


def execute_transformation(callback, metadata_path, transform):
    """Transform a metadata file with the given transformation function."""
    coll, data = os.path.split(metadata_path)

    group_name = metadata_path.split('/')[3]

    metadata = jsonutil.read(callback, metadata_path)
    metadata = transform(metadata)

    if group_name.startswith('research-'):
        backup = '{}/transformation-backup[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in research {}, backup @ {}'.format(metadata_path, backup))
        msi.data_obj_copy(callback, metadata_path, backup, '', irods_types.BytesBuf())
        jsonutil.write(callback, metadata_path, metadata)
    elif group_name.startswith('vault-'):
        new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
        jsonutil.write(callback, new_path, metadata)
        copy_acls_from_parent(callback, new_path, "default")
        callback.rule_provenance_log_action("system", coll, "updated metadata schema")
        log.write(callback, "Transformed %s" % (new_path))
    else:
        raise AssertionError()


def transform_research_xml(callback, xml_path):
    """
    Transform a yoda-metadata XML to JSON in the research area.

    Note: This assumes no yoda-metadata.json exists yet - otherwise it will be overwritten.

    :returns: API status
    """
    _, zone, _1, _2 = pathutil.info(xml_path)
    xml_data = xmltodict.parse(data_object.read(callback, xml_path))

    try:
        xml_ns = xml_data['metadata']['@xmlns']
        schema_category = xml_ns.split('/')[-1]
    except KeyError as e:
        if e.args[0] != '@xmlns':
            raise
        # Previous default-0 compliant metadata XML had no schema indication.
        # Set to default-0 for backwards compat.
        xml_ns = 'https://yoda.uu.nl/schemas/default-0'
        schema_category = xml_ns.split('/')[-1]
    except Exception as e:
        return api.Error('bad_xml', 'XML metadata file is malformed', debug_info=repr(e))

    try:
        json_schema_path = '/' + zone + '/yoda/schemas/' + schema_category + '/metadata.json'
        schem = jsonutil.read(callback, json_schema_path)
    except error.UUFileNotExistError:
        return api.Error('missing_schema',
                         'Metadata schema for default-0 is needed for XML transformation. Please contact an administrator.')

    try:
        # FIXME: This should get a dict instead of a json string.
        metadata = jsonutil.parse(vault_xml_to_json.transformYodaXmlDataToJson(callback, schem, xml_data))
        # FIXME: schema id should be inserted by the transformer instead.
        schema_id = xml_ns + '/metadata.json'
        meta.metadata_set_schema_id(metadata, schema_id)

        try:
            schem = schema.get_schema_by_id(callback, schema_id, xml_path)
        except Exception as e:
            log.write(callback, 'Warning: could not get JSON schema for XML <{}> with schema_id <{}>: {}'
                      .format(xml_path, schema_id, str(e)))
            # The result is unusable, as there will be no possible JSON → JSON
            # transformation that will make this a valid metadata file.
            raise e  # give up.

        json_path = re.sub('\.xml$', '.json', xml_path)

        # Validate against the metadata's indicated schema.
        # This is purely for logging / debugging currently,
        # any validation errors will be reported when the form is next opened.
        errors = meta.get_json_metadata_errors(callback,
                                               json_path,
                                               metadata=metadata,
                                               schema=schem,
                                               ignore_required=True)

        if len(errors) > 0:
            # This is not fatal - there may have been validation errors in the XML as well,
            # which should remain exactly the same in the new JSON situation.
            # print(errors)
            log.write(callback, 'Warning: Validation errors exist after transforming XML to JSON (<{}> with schema id <{}>), continuing'
                      .format(xml_path, schema_id))

        jsonutil.write(callback, json_path, metadata)
    except Exception as e:
        return api.Error('bad_xml', 'XML metadata file could not be transformed', debug_info=repr(e))


@api.make()
def api_transform_metadata(ctx, coll):
    """Transform a yoda-metadata file in the given collection to the active schema."""
    metadata_path = meta.get_collection_metadata_path(ctx, coll)

    if metadata_path is None:
        return api.Error('no_metadata', 'No metadata file found')
    elif metadata_path.endswith('.xml'):
        # XML metadata.

        space, _0, _1, _2 = pathutil.info(metadata_path)
        if space != pathutil.Space.RESEARCH:
            # Vault XML metadata is not transformed through this path, currently.
            log.write(ctx, 'vault metadata transformation not supported via API, currently')
            return api.Error('internal', 'Internal error')

        # Special case: Transform legacy XML metadata to JSON equivalent.
        # If the metadata is in default-0 format and the active schema is
        # newer, a second transformation will be needed, and the user will be
        # prompted for that the next time they open the form.
        log.write(ctx, 'Transforming XML -> JSON in the research space')
        return transform_research_xml(ctx, metadata_path)
    else:
        # JSON metadata.
        log.write(ctx, 'Transforming JSON -> JSON in the research space')
        transform = get(ctx, metadata_path)

        if transform is None:
            return api.Error('undefined_transformation', 'No transformation found')

        execute_transformation(ctx, metadata_path, transform)


def get(callback, metadata_path, metadata=None):
    """Find a transformation that can be executed on the given metadata JSON.

    :returns: Transformation function on success, or None if no transformation was found
    """
    try:
        src = schema.get_schema_id(callback, metadata_path, metadata=metadata)
        dst = schema.get_active_schema_id(callback, metadata_path)

        # Ideally, we would check that the metadata is valid in its current
        # schema before claiming that we can transform it...

        # print('{} -> {}'.format(src,dst))

        return schema_transformations.get(src, dst)
    except KeyError as e:
        return None
    except error.UUError as e:
        # print('{} -> {} ERR {}'.format(src,dst, e))
        return None


# TODO: @rule.make
def rule_get_transformation_info(rule_args, callback, rei):
    """
    Check if a yoda-metadata.json transformation is possible and if so, retrieve transformation description.

    :param rule_args[0]: JSON path

    :param rule_args[1]: Transformation possible? true|false
    :param rule_args[2]: human-readable description of the transformation
    """
    json_path = rule_args[0]

    rule_args[1:3] = 'false', ''

    transform = get(callback, json_path)

    if transform is not None:
        rule_args[1:3] = 'true', transformation_html(transform)


def copy_acls_from_parent(callback, path, recursive_flag):
    """
    When inheritance is missing we need to copy ACLs when introducing new data in vault package.

    :param path: Path of object that needs the permissions of parent
    :param recursive_flag: Either "default" for no recursion or "recursive"
    """
    parent = os.path.dirname(path)

    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        access_name = row[0]
        user_id = int(row[1])

        user_name = user.name_from_id(callback, user_id)

        if access_name == "own":
            log.write(callback, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "own", user_name, path)
        elif access_name == "read object":
            log.write(callback, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "read", user_name, path)
        elif access_name == "modify object":
            log.write(callback, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "write", user_name, path)


# TODO: @rule.make
def rule_batch_transform_vault_metadata(rule_args, callback, rei):
    """
    Transform all metadata JSON files in the vault to the active schema.

    :param coll_id: First COLL_ID to check
    :param batch: Batch size, <= 256
    :param pause: Pause between checks (float)
    :param delay: Delay between batches in seconds
    """
    coll_id = int(rule_args[0])
    batch   = int(rule_args[1])
    pause   = float(rule_args[2])
    delay   = int(rule_args[3])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one batch of metadata schemas.

    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_NAME like 'yoda-metadata%%json' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        genquery.AS_LIST, callback)

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        path_parts = coll_name.split('/')

        try:
            group_name = path_parts[3]
            # Get vault package path.
            vault_package = '/'.join(path_parts[:5])
            metadata_path = meta.get_latest_vault_metadata_path(callback, vault_package)
            if metadata_path  != '':
                transform = get(callback, metadata_path)
                if transform is not None:
                    execute_transformation(callback, metadata_path, transform)
        except Exception:
            pass

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id += 1
    else:
        # All done.
        coll_id = 0
        log.write(callback, "[METADATA] Finished updating metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_transform_vault_metadata('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


def html(f):
    """Get a human-readable HTML description of a transformation function.

    The text is derived from the function's docstring.

    :returns: Human-readable HTML description of a transformation function
    """
    return '\n'.join(map(lambda paragraph:
                     '<p>{}</p>'.format(  # Trim whitespace.
                         re.sub('\s+', ' ', paragraph).strip()),
                         # Docstring paragraphs are separated by blank lines.
                         re.split('\n{2,}', f.__doc__)))
