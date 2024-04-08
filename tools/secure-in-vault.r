#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
#
# This script can be used to manually secure a data package in the vault after
# it has been fixed manually. The default input parameter values are examples.

yodaSecureFolder {
    rule_folder_secure("*researchCollection","*vaultCollection");
}

input *researchCollection="/zoneName/home/research-groupname/packagename", *vaultCollection="/zoneName/home/vault-groupname/packagename[1234567890]"
output ruleExecOut
