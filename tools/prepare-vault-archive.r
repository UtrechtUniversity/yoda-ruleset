#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
prepareVaultArchive {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*status = "";
	if (*action == "download") {
		rule_vault_download(*actor, *coll, *status);
	} else {
		rule_vault_archive(*actor, *coll, *action, *status);
	}
	writeLine("stdout", "*actor archive *coll *action: *status");
}

input *actor="", *coll="", *action=""
output ruleExecOut
