#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Generate Data Package References (UUID4) for vault packages without a reference.
#
import uuid

import genquery


def main(rule_args, callback, rei):
    callback.writeLine("serverLog", "Start generating Data Package References for vault packages")
    callback.writeLine("serverLog", "------------------------------------")

    # Retrieve all vault packages.
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME not like '%/original' AND META_COLL_ATTR_NAME = 'org_vault_status'",
        genquery.AS_LIST, callback)

    for row in iter:
        has_yoda_reference = False
        data_package = row[0]

        # Check if vault package has Data Package Reference.
        iter2 = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'org_data_package_reference'".format(data_package),
            genquery.AS_LIST, callback)

        for row2 in iter2:
            has_yoda_reference = True

        # Generate Data Package Reference if data package has no reference.
        if not has_yoda_reference:
            callback.writeLine("serverLog", "Data Package: {}".format(data_package))

            try:
                reference = str(uuid.uuid4())
                out = callback.msiString2KeyValPair("org_data_package_reference={}".format(reference), 0)
                kvp = out['arguments'][1]
                callback.msiSetKeyValuePairsToObj(kvp, data_package, '-C')
                callback.writeLine("serverLog", "Data Package Reference: {}".format(reference))
            except Exception:
                callback.writeLine("serverLog", "Something went wrong generating the Data Package Reference.")

            callback.writeLine("serverLog", "------------------------------------")

    callback.writeLine("serverLog", "Finished generating Data Package References for vault packages")


INPUT null
OUTPUT ruleExecOut
