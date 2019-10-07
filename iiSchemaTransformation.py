# \file      iiSchemaTransformation.py
# \brief     Functions for handling schema updates within any yoda-metadata file.
# \author    Lazlo Westerhof
# \author    Felix Croes
# \author    Harm de Raaff
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import os
from collections import namedtuple
from enum import Enum
import hashlib
import base64
import json
import irods_types
import time

import genquery
import session_vars


def execute_transformation(callback, metadata_path, transform):
    coll, data = os.path.split(metadata_path)

    group_name = metadata_path.split('/')[3]

    metadata = read_json_object(callback, metadata_path)
    metadata = transform(metadata)

    if group_name.startswith('research-'):
        backup = '{}/transformation-backup[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in research {}, backup @ {}'.format(metadata_path, backup))
        data_obj_copy(callback, metadata_path, backup, '', irods_types.BytesBuf())
        write_json_object(callback, metadata_path, metadata)
    elif group_name.startswith('vault-'):
        new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
        write_json_object(callback, new_path, metadata)
        copy_acls_from_parent(callback, new_path, "default")
        callback.iiAddActionLogRecord("system", coll, "updated metadata schema")
        callback.writeString("serverLog", "Transformed %s" % (new_path))
    else:
        assert False

# ----------------------------------- interface functions when calling from irods rules have prefix iiRule

def iiRuleTransformMetadata(rule_args, callback, rei):
    """Transform a yoda-metadata.json to the active schema.

       Arguments:
       rule_args[0] -- JSON path

       Return:
       rule_args[1] -- statusPy
       rule_args[2] -- statusInfoPy
    """
    metadata_path = rule_args[0] + "/yoda-metadata.json"
    transform = get_transformation(callback, metadata_path)

    if transform is None:
        rule_args[1:3] = 'ERROR', 'No transformation found'
        return

    execute_transformation(callback, metadata_path, transform)


def get_transformation(callback, metadata_path, metadata = None):
    """Find a transformation that can be executed on the given metadata JSON.
       Returns a transformation function on success, or None if no transformation was found.
    """
    try:
        src = get_schema_id(callback, metadata_path, metadata = metadata)
        dst = get_active_schema_id(callback, metadata_path)

        # Ideally, we would check that the metadata is valid in its current
        # schema before claiming that we can transform it...

        # print('{} -> {}'.format(src,dst))

        return transformations[src][dst]
    except:
        return None


def iiGetTransformationInfo(rule_args, callback, rei):
    """Check if a yoda-metadata.json transformation is possible and if so,
       retrieve transformation description.

       Arguments:
       rule_args[0] -- JSON path

       Return:
       rule_args[1] -- transformation possible? true|false
       rule_args[2] -- human-readable description of the transformation
    """
    json_path = rule_args[0]

    rule_args[1:3] = 'false', ''

    transform = get_transformation(callback, json_path)

    if transform is not None:
        rule_args[1:3] = 'true', transformation_html(transform)

# ------------------ end of interface functions -----------------------------

def iiRuleGetLocation(rule_args, callback, rei):
    """Return the metadata schema location based upon the category of a metadata JSON.

       Example:
       in:  /tempZone/home/research-initial/yoda-metadata.json
       out: 'https://yoda.uu.nl/schemas/default-0'

       Arguments:
       rule_args[0] -- Path of metadata JSON

       Return:
       rule_args[1] -- Metadata schema location
    """
    rule_args[1] = get_active_schema_id(callback, rule_args[0])


def copy_acls_from_parent(callback, path, recursive_flag):
    """When inheritance is missing we need to copy ACLs when introducing new data in vault package.

       Arguments:
       path           -- Path of object that needs the permissions of parent
       recursive_flag -- Either "default" for no recursion or "recursive"
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

        user_name = user_name_from_id(callback, user_id)

        if access_name == "own":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "own", user_name, path)
        elif access_name == "read object":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "read", user_name, path)
        elif access_name == "modify object":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "write", user_name, path)


def iiBatchTransformVaultMetadata(rule_args, callback, rei):
    """Transform all metadata JSON files in the vault to the active schema.

       Arguments:
       coll_id -- first COLL_ID to check
       batch   -- batch size, <= 256
       pause   -- pause between checks (float)
       delay   -- delay between batches in seconds
    """
    coll_id = int(rule_args[0])
    batch = int(rule_args[1])
    pause = float(rule_args[2])
    delay = int(rule_args[3])
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
            metadata_path = get_latest_vault_metadata_path(callback, vault_package)
            if metadata_path  != '':
                transform = get_transformation(callback, metadata_path)
                if transform is not None:
                    execute_transformation(callback, metadata_path, transform)
        except:
            pass

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id = coll_id + 1
    else:
        # All done.
        coll_id = 0
        callback.writeString("serverLog", "[METADATA] Finished updating metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "iiBatchTransformVaultMetadata('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")
