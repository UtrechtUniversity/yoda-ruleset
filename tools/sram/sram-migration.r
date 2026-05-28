#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# Migrates groups between SRAM and non-SRAM by reading from a CSV file.
#
import csv

def main(rule_args, callback, rei):
    log_loc = global_vars["*log_loc"]
    dry_run = global_vars["*dry_run"]
    target_group_type = global_vars["*target_group_type"]
    file_name = global_vars["*file_name"]

    with open(file_name, "r") as read_groups:
        groups = csv.reader(read_groups)

        for row in groups:
            callback.writeLine("stdout", row[0])
            callback.rule_sram_migration(log_loc, dry_run, target_group_type, row[0])


input *log_loc="", *dry_run="", *target_group_type= "non-sram", *file_name="/etc/irods/yoda-ruleset/tools/sram/test-sram-migration.csv"
output ruleExecOut
