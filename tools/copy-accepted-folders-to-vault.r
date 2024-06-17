#!/usr/bin/irule -F

copyToVault {
	# Copy research folder to vault.
	# This script is kept as dumb as possible.
	# All processing and error handling is done by rule_vault_copy_accepted_to_vault
	*state = "CRONJOB_PENDING"
	rule_vault_copy_to_vault(*state);
}
input null
output ruleExecOut
