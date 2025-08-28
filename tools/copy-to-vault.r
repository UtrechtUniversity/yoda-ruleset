#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F

copyToVault {
    # Try to copy accepted and retry research folders to vault.
    # This script is kept as dumb as possible.
    # All processing and error handling is done by rule_vault_copy_to_vault
    rule_vault_copy_to_vault();
}

INPUT null
OUTPUT ruleExecOut
