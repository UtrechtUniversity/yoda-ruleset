#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Generate Data Package References (UUID4) for vault packages without a reference.
#
import uuid

import genquery
from tstrings import t


def main(rule_args, callback, rei):
    callback.writeString("serverLog", "Start generating Data Package References for vault packages")
    callback.writeString("serverLog", "------------------------------------")

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
            t("COLL_NAME = '{data_package}' AND META_COLL_ATTR_NAME = 'org_data_package_reference'"),
            genquery.AS_LIST, callback)

        for row2 in iter2:
            has_yoda_reference = True

        # Generate Data Package Reference if data package has no reference.
        if not has_yoda_reference:
            callback.writeString("serverLog", f"Data Package: {data_package}")

            try:
                reference = str(uuid.uuid4())
                out = callback.msiString2KeyValPair(f"org_data_package_reference={reference}", 0)
                kvp = out['arguments'][1]
                callback.msiSetKeyValuePairsToObj(kvp, data_package, '-C')
                callback.writeString("serverLog", f"Data Package Reference: {reference}")
            except Exception:
                callback.writeString("serverLog", "Something went wrong generating the Data Package Reference.")

            callback.writeString("serverLog", "------------------------------------")

    callback.writeString("serverLog", "Finished generating Data Package References for vault packages")


INPUT null
OUTPUT ruleExecOut
