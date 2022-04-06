#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
removeVaultIndexing {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'vault-%') {
		*vaultGroupName = *row.USER_NAME;		
		*vaultHome = "/" ++ $rodsZoneClient ++ "/home/" ++ *vaultGroupName;
		if (uuCollectionExists(*vaultHome)) {
			foreach (*row2 in SELECT COLL_NAME WHERE COLL_PARENT_NAME = *vaultHome) {
				msiExecCmd("disable-indexing.sh", *row2.COLL_NAME, "", "", 0, *out);
			}
		}
	}
}

input null
output ruleExecOut
