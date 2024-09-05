#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Run the integration tests (must be run on a development environment)
#
import genquery


def main(rule_args, callback, rei):
    tests = global_vars["*tests"].strip('"')
    result = callback.rule_run_integration_tests(tests, "")
    callback.writeLine("stdout", result["arguments"][1])


INPUT *tests=""
OUTPUT ruleExecOut
