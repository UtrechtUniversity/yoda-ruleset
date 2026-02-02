#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Check and update metadata of data package to active metadata schema
#
# Example command to run:
# irule -r irods_rule_engine_plugin-python-instance -F tools/check-single-dp-metadata-for-schema-updates.r '*collection="/tempZone/home/vault-foo/datapackage[123456789]"'
def main(rule_args, callback, rei):
    collection = global_vars["*collection"][1:-1]

    if collection == "":
        callback.writeLine("stdout", "Error: this rule needs a collection parameter value to run.")
        return

    result = callback.rule_transform_vault_metadata(collection, '', '')
    callback.writeLine("stdout", "OK" if result['arguments'][1] == "0"
	               else "Error: " + result['arguments'][2])

INPUT *collection=""
OUTPUT ruleExecOut
