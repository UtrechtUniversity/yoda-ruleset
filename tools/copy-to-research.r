#!/usr/bin/irule -F
# FIXME: the comments are not updated
copyToVault {
	# Try to copy accepted and retry research folders to vault.
	# This script is kept as dumb as possible.
	# All processing and error handling is done by rule_vault_copy_to_research
	rule_vault_copy_to_research();
}
input null
output ruleExecOut
