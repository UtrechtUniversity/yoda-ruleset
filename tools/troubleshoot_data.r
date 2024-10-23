#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

def main(rule_args, callback, rei):
    data_package = global_vars["*data_package"].strip('"')
    log_loc = global_vars["*log_loc"].strip('"')
    offline = global_vars["*offline"].strip('"')
    no_datacite = global_vars["*no_datacite"].strip('"')
    callback.rule_batch_troubleshoot_published_data_packages(data_package, log_loc, offline, no_datacite)

INPUT *data_package="", *log_loc="", *offline="", *no_datacite=""
OUTPUT ruleExecOut
