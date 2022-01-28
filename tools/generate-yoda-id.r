#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Generate Yoda ID (UUID4) for vault package without a Yoda ID.
#
import uuid

import genquery


def main(rule_args, callback, rei):
    callback.writeLine("serverLog", "Start generating Yoda IDs for vault packages")
    callback.writeLine("serverLog", "------------------------------------")

    # Retrieve all vault packages.
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME not like '%/original' AND META_COLL_ATTR_NAME = 'org_vault_status'",
        genquery.AS_LIST, callback)

    for row in iter:
        has_yoda_id = False
        data_package = row[0]

        # Check if vault package has Yoda ID.
        iter2 = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'org_yoda_id'".format(data_package),
            genquery.AS_LIST, callback)

        for row2 in iter2:
            has_yoda_id = True

        # Generate Yoda ID if data package has no Yoda ID.
        if not has_yoda_id:
            callback.writeLine("serverLog", "Data Package: {}".format(data_package))

            try:
                yoda_id = str(uuid.uuid4())
                out = callback.msiString2KeyValPair("org_yoda_id={}".format(yoda_id), 0)
                kvp = out['arguments'][1]
                callback.msiSetKeyValuePairsToObj(kvp, data_package, '-C')
                callback.writeLine("serverLog", "Yoda ID: {}".format(yoda_id))
            except Exception:
                callback.writeLine("serverLog", "Something went wrong generating the Yoda ID.")

            callback.writeLine("serverLog", "------------------------------------")

    callback.writeLine("serverLog", "Finished generating Yoda IDs for vault packages")


INPUT null
OUTPUT ruleExecOut
