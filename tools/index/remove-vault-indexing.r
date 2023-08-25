#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
removeVaultIndexing {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*vaultHome = "/" ++ $rodsZoneClient ++ "/home/vault-pilot";
	if (uuCollectionExists(*vaultHome)) {
		foreach (*row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = *vaultHome) {
			*coll = *row.COLL_NAME;
			*out = "";
			rule_vault_disable_indexing(*coll, *out);
		}
	}
}

input null
output ruleExecOut
