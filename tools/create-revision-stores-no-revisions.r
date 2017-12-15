#!/usr/bin/irule -F
createRevisionStoresNoRevisions {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'research-%') {
		*groupName = *row.USER_NAME;

		*revisionStore = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION ++ "/" ++ *groupName;
		if (!uuCollectionExists(*revisionStore)) {
			writeLine("stdout", "Creating *revisionStore");
			msiCollCreate(*revisionStore, 1, *status);
			msiSetACL("recursive", "own", *groupName, *revisionStore);
			

		}

	}
}

input null
output ruleExecOut
