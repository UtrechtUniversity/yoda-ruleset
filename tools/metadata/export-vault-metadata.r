#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Export vault data package metadata as JSON.
#
# For every vault data package the following is exported:
#
# path      iRODS collection path of vault data package
# modified  Last modified datetime of vault data package
# doi       DataCite DOI of vault data package (when published)
# size      Size in bytes of vault data package
# schema    Schema used for metadata in vault data package
# metadata  Metadata of vault data package
#
import itertools
import json
import sys
if sys.version_info > (2, 7):
    from functools import reduce
from collections import OrderedDict
from datetime import datetime

import genquery
import irods_types


def get_size(ctx, path):
    """Get a collection's size in bytes.

    :param ctx:  iRODS context
    :param path: Path to vault package

    :return: Data package size in bytes
    """
    def func(x, row):
        return x + int(row[1])

    return reduce(func,
                  itertools.chain(genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}'".format(path),
                                                        genquery.AS_LIST, ctx),
                                  genquery.row_iterator("DATA_ID, DATA_SIZE",
                                                        "COLL_NAME like '{}/%'".format(path),
                                                        genquery.AS_LIST, ctx)), 0)


def get_doi(ctx, path):
    """Get the DOI of a data package in the vault.

    :param ctx:  iRODS context
    :param path: Vault package to get the DOI of

    :return: Data package DOI or None
    """
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_versionDOI'" % (path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_latest_vault_metadata_path(ctx, path):
    """
    Get the latest vault metadata JSON file.

    :param ctx:  iRODS context
    :param path: Vault package collection

    :returns: Metadata JSON path
    """
    name = None

    iter = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME = '{}' AND DATA_NAME like 'yoda-metadata[%].json'".format(path),
        genquery.AS_LIST, ctx)

    for row in iter:
        data_name = row[0]
        if name is None or (name < data_name and len(name) <= len(data_name)):
            name = data_name

    return None if name is None else '{}/{}'.format(path, name)


def get_metadata_as_dict(ctx, path):
    """
    Get the vault metadata as dict.

    :param ctx:  iRODS context
    :param path: Path to metadata file

    :returns: Metadata as dict
    """
    # Open iRODS file
    ret_val = ctx.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val['arguments'][1]

    # Read iRODS file
    ret_val = ctx.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val['arguments'][2]

    # Convert BytesBuffer to string
    ret_val = ctx.msiBytesBufToStr(read_buf, "")
    output_json = ret_val['arguments'][1]

    # Close iRODS file
    ctx.msiDataObjClose(file_desc, 0)

    return json.loads(output_json)


def get_last_modified_datetime(ctx, vault_package):
    """Determine the time of last modification as a datetime with UTC offset.

    :param ctx:           iRODS context
    :param vault_package: Path to the package in the vault

    :return: Last modified date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = 'org_action_log'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        log_item_list = json.loads(row[1], object_pairs_hook=OrderedDict)

        my_date = datetime.fromtimestamp(int(log_item_list[0]))

        return my_date.strftime('%Y-%m-%dT%H:%M:%S%z')


def main(rule_args, ctx, rei):
    package_statuses = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = 'org_vault_status' "
        "AND COLL_NAME not like '%/original'",
        genquery.AS_TUPLE,
        ctx)

    package_schemas = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = 'href' "
        "AND COLL_NAME not like '%/original'",
        genquery.AS_TUPLE,
        ctx)

    metadata_export = OrderedDict([])
    for (path, status) in package_statuses:
        try:
            ctx.writeLine("serverLog", "[export] Collecting metadata for vault data package {}".format(path))
            vault_metadata = OrderedDict()

            # Path
            vault_metadata['path'] = path

            # Modified date
            vault_metadata['modified'] = get_last_modified_datetime(ctx, path)

            # DOI
            doi = get_doi(ctx, path)
            if doi:
                vault_metadata['doi'] = "https://doi.org/{}".format(doi)

            # Package size
            vault_metadata['size'] = get_size(ctx, path)

            # Metadata schema
            schema = None
            for (path_, schema_) in package_schemas:
                if path == path_:
                    schema = schema_
                    break
            vault_metadata['schema'] = schema

            # Metadata
            metadata_data_object = get_latest_vault_metadata_path(ctx, path)
            vault_metadata['metadata'] = get_metadata_as_dict(ctx, metadata_data_object)

            metadata_export[path] = vault_metadata
        except Exception:
            ctx.writeLine("serverLog", "[export] Error collecting metadata for vault data package {}".format(path))
    ctx.writeLine("stdout", json.dumps(metadata_export, indent=4))

INPUT null
OUTPUT ruleExecOut
