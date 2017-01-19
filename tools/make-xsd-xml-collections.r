createXmlXsdCollections {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*isfound = false;
	*xsdcoll = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *xsdcoll) {
		*isfound = true;
	}
	if(*isfound) {
		writeLine("stdout", "System collection already exists at: *xsdcoll");
	} else {
		msiCollCreate(*xsdcoll, 1, *status);
		msiSetACL("default", "admin:read", "public", *xsdcoll);
		msiSetACL("default", "admin:inherit", "public", *xsdcoll);
	}

	*isfound = false;
	*xmlcoll = "/" ++ $rodsZoneClient ++ IIXMLCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *xmlcoll) {
		*isfound = true;
	}
	if(*isfound) {
		writeLine("stdout", "System collection already exists at: *xmlcoll");
	} else {
		msiCollCreate(*xmlcoll, 1, *status);
		msiSetACL("default", "read", "public", *xmlcoll);
		msiSetACL("default", "admin:inherit", "public", *xmlcoll);
	}
	
}

input null
output ruleExecOut
