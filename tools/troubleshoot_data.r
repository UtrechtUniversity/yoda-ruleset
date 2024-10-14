#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

def main(rule_args, callback, rei):
    data_package = global_vars["*data_package"].strip('"')
    log_loc = global_vars["*log_loc"].strip('"')
    callback.rule_batch_troubleshoot_published_data_packages(data_package, log_loc)

INPUT *data_package="", *log_loc=""
OUTPUT ruleExecOut
