#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# Correct vault data package metadata containing invalid ORCID person identifiers.
#
check {
        writeLine("serverLog", "[METADATA] Start correcting ORCID format in person identifers.");
        rule_batch_vault_metadata_correct_orcid_format("0", *batch, *pause, *delay);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut
