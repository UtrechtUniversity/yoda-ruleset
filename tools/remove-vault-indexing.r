removeVaultIndexing {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'vault-%') {
		*vaultGroupName = *row.USER_NAME;		
		*vaultHome = "/" ++ $rodsZoneClient ++ "/home/" ++ *vaultGroupName;
		if (uuCollectionExists(*vaultHome)) {
			msiExecCmd("disable-indexing.sh", *vaultHome, "", "", 0, *out);
		}
	}
}

input null
output ruleExecOut
