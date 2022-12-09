#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
vaultArchive {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_archival_status' AND META_COLL_ATTR_VALUE = 'archiving') {
		*coll = *row.COLL_NAME;
		break;
	}
	rule_vault_create_archive(*coll);
}

input null
output ruleExecOut
