#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F 
#
verifyChecksum() {
    verifyChecksumBatch(0, *max, *update);
}

input *max=1, *update=0
output ruleExecOut
