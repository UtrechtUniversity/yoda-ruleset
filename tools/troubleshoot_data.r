#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
import csv
import io
import json
import genquery

def main(rule_args, callback, rei):
    data_package = global_vars["*data_package"].strip('"')
    callback.rule_batch_troubleshoot_published_data_packages(data_package)

INPUT *data_package=all_published_packages
OUTPUT ruleExecOut
