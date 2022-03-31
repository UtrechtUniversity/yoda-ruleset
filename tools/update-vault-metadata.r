#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
updateVaultMetadata {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'vault-%') {
		*vaultGroupName = *row.USER_NAME;
		*vaultHome = "/" ++ $rodsZoneClient ++ "/home/" ++ *vaultGroupName;
		if (uuCollectionExists(*vaultHome)) {
			foreach (*row2 in SELECT COLL_NAME, COLL_ID WHERE COLL_PARENT_NAME = *vaultHome) {

				*coll = *row2.COLL_NAME;
				*id = *row2.COLL_ID;
				foreach (*row3 in SELECT DATA_NAME WHERE DATA_COLL_ID = "*id" AND DATA_NAME LIKE "yoda-metadata%") {
					*data = *row3.DATA_NAME;
					rule_meta_modified_post("*coll/*data", $userNameClient, $rodsZoneClient);
				}
			}
		}
	}
}

input null
output ruleExecOut
