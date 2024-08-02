#!/usr/bin/irule -F

grantReadersAccessVaultPackages {
	# Grant read- groups access to corresponding vault packages
    *return = "";
    rule_vault_grant_readers_vault_access(*dryRun, *verbose, *return);
}
input *dryRun="", *verbose=""
output ruleExecOut
