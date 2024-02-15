#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Run the integration tests (must be run on a development environment)
#
import genquery


def main(rule_args, callback, rei):
    result = callback.rule_run_integration_tests("")
    callback.writeLine("stdout", result["arguments"][0])


INPUT null
OUTPUT ruleExecOut
