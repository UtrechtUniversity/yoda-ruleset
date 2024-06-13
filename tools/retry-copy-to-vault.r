retryCopyToVault {
	# Copy research folder to vault.
	# This script is kept as dumb as possible.
	# All processing and error handling is done by rule_vault_copy_accepted_retry_to_vault
	*state = "CRONJOB_RETRY"
	rule_vault_copy_to_vault(*state);
}
input null
output ruleExecOut
