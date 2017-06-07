setVaultPermissions {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'vault-%') {
		*vaultGroupName = *row.USER_NAME;		
		*vaultHome = "/" ++ $rodsZoneClient ++ "/home/" ++ *vaultGroupName;
		if (uuCollectionExists(*vaultHome)) {
			uuGetBaseGroup(*vaultGroupName, *baseGroup);
			if (*baseGroup like "research-*") {
				writeLine("stdout", "Disabling inheritance for *vaultHome");
				msiSetACL("default", "admin:noinherit", uuClientFullName, *vaultHome);


				writeLine("stdout", "Granting read acccess to *vaultHome for *baseGroup");
				msiSetACL("default", "admin:read", *baseGroup, *vaultHome);	
			}
		}
	}
}

input null
output ruleExecOut
