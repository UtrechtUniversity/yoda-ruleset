createSystemCollection {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}
	
	*systemcolls = list("/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION)

	if (*enableRevisions == 1) {
		*systemcolls = uuListReverse(cons("/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION, *systemcolls));
	}

        if (*enableDatarequest == 1) {
		*systemcolls = uuListReverse(cons("/" ++ $rodsZoneClient ++ UUDATAREQUESTCOLLECTION, *systemcolls));
        }

	foreach(*systemcoll in *systemcolls) {
		*exists = false;
		foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *systemcoll) {
			*exists = true
		}

		if (*exists) {
			writeLine("stdout", "*systemcoll already exists");
		} else {
			writeLine("stdout", "Creating *systemcoll");
			msiCollCreate(*systemcoll, 1, *status);
		}
	}
}

input *enableRevisions=0
output ruleExecOut
