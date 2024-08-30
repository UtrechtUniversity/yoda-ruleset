#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

def main(rule_args, callback, rei):
    data_package = global_vars["*data_package"].strip('"')
    print("data_package from .r",data_package)

    callback.rule_batch_troubleshoot_published_data_packages(data_package)

# Published data package example:"/tempZone/home/vault-core-0/research-core-0[1722266819]"
INPUT *data_package=all_published_packages
OUTPUT ruleExecOut
