#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
prepareVaultArchive {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	rule_vault_archive(*actor, *coll, *status);
	writeLine("stdout", "*actor archive *coll: *status");
}

input null
output ruleExecOut
