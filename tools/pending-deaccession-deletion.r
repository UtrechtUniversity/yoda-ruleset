#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F

pendingDeaccessionDeletion {
    # Check for deaccessioned data packages waiting for data deletion
    rule_pending_deaccession_deletion();
}

INPUT null
OUTPUT ruleExecOut
