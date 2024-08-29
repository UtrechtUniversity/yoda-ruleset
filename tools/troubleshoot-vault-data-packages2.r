#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Prints a report of all vault data packages, their metadata schema
# and whether the current metadata matches the schema. Errors are written
# to the rodsLog.
#
# Output format: CSV, with the following columns:
# 1. Data package collection
# 2. Short schema name (e.g. "default-3")
# 3. Boolean value that indicate whether the metadata matches the schema ("True"/"False")
#

import csv
import io
import json
import genquery


def main(rule_args, callback, rei):
    result = callback.rule_batch_vault_packages_troubleshoot("")

INPUT null
OUTPUT ruleExecOut
