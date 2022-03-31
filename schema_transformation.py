# -*- coding: utf-8 -*-
"""Functions for handling schema updates within any yoda-metadata file."""

__copyright__ = 'Copyright (c) 2018-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_transform_vault_metadata',
           'rule_get_transformation_info',
           'api_transform_metadata']

import os
import re
import time

import genquery
import irods_types
import session_vars

import meta
import schema
import schema_transformations
from util import *


def execute_transformation(ctx, metadata_path, transform):
    """Transform a metadata file with the given transformation function."""
    coll, data = os.path.split(metadata_path)

    group_name = metadata_path.split('/')[3]

    metadata = jsonutil.read(ctx, metadata_path)
    metadata = transform(ctx, metadata)

    if group_name.startswith('research-'):
        backup = '{}/transformation-backup[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in research {}, backup @ {}'.format(metadata_path, backup))
        msi.data_obj_copy(ctx, metadata_path, backup, '', irods_types.BytesBuf())
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
def api_transform_metadata(ctx, coll):
    """Transform a yoda-metadata file in the given collection to the active schema."""
    metadata_path = meta.get_collection_metadata_path(ctx, coll)

    if metadata_path.endswith('.json'):
        # JSON metadata.
        log.write(ctx, 'Transforming JSON -> JSON in the research space')
        transform = get(ctx, metadata_path)

        if transform is None:
            return api.Error('undefined_transformation', 'No transformation found')

        execute_transformation(ctx, metadata_path, transform)
    else:
        return api.Error('no_metadata', 'No metadata file found')


def get(ctx, metadata_path, metadata=None):
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

        return schema_transformations.get(src, dst)
    except KeyError:
        return None
    except error.UUError:
        # print('{} -> {} ERR {}'.format(src,dst, e))
        return None


# TODO: @rule.make
def rule_get_transformation_info(rule_args, callback, rei):
    """Check if a yoda-metadata.json transformation is possible and if so, retrieve transformation description.

    :param rule_args: [0] JSON path
                      [1] Transformation possible? true|false
                      [2] human-readable description of the transformation
    :param callback:  Callback to rule Language
    :param rei:       The rei struct

    """
    json_path = rule_args[0]

    rule_args[1:3] = 'false', ''

    transform = get(callback, json_path)

    if transform is not None:
        rule_args[1:3] = 'true', transformation_html(transform)


def copy_acls_from_parent(ctx, path, recursive_flag):
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

        if access_name == "own":
            log.write(ctx, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            ctx.msiSetACL(recursive_flag, "own", user_name, path)
        elif access_name == "read object":
            log.write(ctx, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            ctx.msiSetACL(recursive_flag, "read", user_name, path)
        elif access_name == "modify object":
            log.write(ctx, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            ctx.msiSetACL(recursive_flag, "write", user_name, path)


# TODO: @rule.make
def rule_batch_transform_vault_metadata(rule_args, callback, rei):
    """
    Transform all metadata JSON files in the vault to the active schema.

    :param rule_args: [0] First COLL_ID to check - initial = 0
                      [1] Batch size, <= 256
                      [2] Pause between checks (float)
                      [3] Delay between batches in seconds
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
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
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_transform_vault_metadata('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


def html(f):
    """Get a human-readable HTML description of a transformation function.

    The text is derived from the function's docstring.

    :param f: Transformation function

    :returns: Human-readable HTML description of a transformation function
    """
    description = '\n'.join(map(lambda paragraph:
                            '<p>{}</p>'.format(  # Trim whitespace.
                                re.sub('\s+', ' ', paragraph).strip()),
                                # Docstring paragraphs are separated by blank lines.
                                re.split('\n{2,}', f.__doc__)))

    # Remove docstring.
    description = re.sub('((:param).*)|((:returns:).*)', ' ', description)

    return description
