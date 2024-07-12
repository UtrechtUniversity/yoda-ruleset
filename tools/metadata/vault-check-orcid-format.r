#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Report vault data package metadata containing invalid ORCID person identifiers.
#
import json
import re

import genquery
import irods_types


def get_metadata_as_dict(callback, path):
    # Open iRODS file
    ret_val = callback.msiDataObjOpen("objPath=" + path, 0)
    file_desc = ret_val['arguments'][1]

    # Read iRODS file
    ret_val = callback.msiDataObjRead(file_desc, 2 ** 31 - 1, irods_types.BytesBuf())
    read_buf = ret_val['arguments'][2]

    # Convert BytesBuffer to string
    ret_val = callback.msiBytesBufToStr(read_buf, "")
    output_json = ret_val['arguments'][1]

    # Close iRODS file
    callback.msiDataObjClose(file_desc, 0)

    return json.loads(output_json)


def main(rule_args, callback, rei):
    # Schemas that have regex validation for ORCIDs, as well as their previous versions.
    # Also includes schemas that don't have validation yet, but might have it in a future version.
    schemas_to_be_checked = ['core-1', 'core-2', 'default-1', 'default-2', 'default-3', 'hptlab-1', 'teclab-1', 'dag-0', 'vollmer-0']

    for schema in schemas_to_be_checked:

        callback.writeLine("stdout", "")
        callback.writeLine("stdout", "SCHEMA: {}".format(schema))

        data_packages = genquery.row_iterator(
            "COLL_NAME",
            "META_COLL_ATTR_NAME = 'href' AND META_COLL_ATTR_VALUE like '%/{}/metadata.json' "
            "AND COLL_NAME not like '%/original' AND COLL_NAME like '/%/home/vault-%' "
            "AND DATA_NAME like 'yoda-metadata%.json'".format(schema),
            genquery.AS_TUPLE,
            callback)

        metadata_files = genquery.row_iterator(
            "COLL_NAME, ORDER_DESC(DATA_NAME)",
            "DATA_NAME like 'yoda-metadata[%].json' "
            "AND COLL_NAME not like '%/original'",
            genquery.AS_TUPLE,
            callback)

        metadata_files_list = [ row for row in metadata_files]

        for coll in data_packages:
            json_file = None

            for (coll_, metadata_file) in metadata_files_list:
                if coll == coll_:
                    json_file = metadata_file
                    break

            wrote_package_line = False

            md = get_metadata_as_dict(callback, coll + '/' + json_file)

            for pi_holder in ['Creator', 'Contributor']:
                if pi_holder in md:
                    for holder in md[pi_holder]:
                        for pi in holder.get('Person_Identifier', []):
                            if pi.get('Name_Identifier_Scheme', None) == 'ORCID':
                                if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", pi['Name_Identifier']):
                                    if not wrote_package_line:
                                        # Only write this line once
                                        callback.writeLine("stdout", '----------------------------------')
                                        callback.writeLine("stdout", "Package: {}".format(coll))
                                        wrote_package_line = True

                                    callback.writeLine("stdout", "Invalid ORCID: \"{}\"".format(pi['Name_Identifier']))
            if wrote_package_line:
                callback.writeLine("stdout", '----------------------------------')


INPUT null
OUTPUT ruleExecOut
