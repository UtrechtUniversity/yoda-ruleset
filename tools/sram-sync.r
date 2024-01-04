#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
sramSync() {
    rule_group_sram_sync();
}

input null
output ruleExecOut
