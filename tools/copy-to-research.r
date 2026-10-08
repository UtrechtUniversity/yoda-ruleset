#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F

copyToResearch {
    # Try to copy vault data package to research.
    # This script is kept as dumb as possible.
    # All processing and error handling is done by rule_vault_copy_to_research
    rule_vault_copy_to_research(*coll_origin_b64, *coll_target_b64, *receiver_b64, *retry_str_b64);
}

INPUT *actor="", *coll_origin_b64="", *coll_target_b64="", *receiver_b64="", *retry_str_b64=""
OUTPUT ruleExecOut
