#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
vaultArchive {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_archival_status' AND META_COLL_ATTR_VALUE = 'archive') {
		*coll = *row.COLL_NAME;
		*status = "";
		rule_vault_create_archive(*coll, *status);
		writeLine("stdout", "create archive for *coll: *status");
	}

	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_archival_status' AND META_COLL_ATTR_VALUE = 'extract') {
		*coll = *row.COLL_NAME;
		*status = "";
		rule_vault_extract_archive(*coll, *status);
		writeLine("stdout", "extract archive for *coll: *status");
	}

	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_archival_status' AND META_COLL_ATTR_VALUE = 'update') {
		*coll = *row.COLL_NAME;
		*status = "";
		rule_vault_update_archive(*coll, *status);
		writeLine("stdout", "update archive for *coll: *status");
	}
}

input null
output ruleExecOut
