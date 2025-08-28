#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F

copyToResearch {
    # Try to copy vault data package to research.
    # This script is kept as dumb as possible.
    # All processing and error handling is done by rule_vault_copy_to_research
    rule_vault_copy_to_research(*coll_origin, *coll_target, *receiver, *retry_str);
}

INPUT *actor="", *coll_origin="", *coll_target="", *receiver="", *retry_str=""
OUTPUT ruleExecOut
