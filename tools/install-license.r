installLicense {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*isfound = false;
	foreach(*row in SELECT RESC_NAME WHERE RESC_NAME = *resc) {
		*isfound = true;
	}

	if (!*isfound) {
		writeLine("stdout", "Resource *resc is not found. Please provide a valid resource example:");
		writeLine("stdout", "irule -F ./install-license.r '\*resc=\"demoResc\"'");
		failmsg(-1, "Aborting. Resource not found");
	}

	if (*license == "") {
		writeLine("stdout", "\*license argument missing");
	}	
	if (*url == "") {
		writeLine("stdout", "\*url argument missing");
	}



	*isfound = false;
	*systemcoll = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *systemcoll) {
		*isfound = true;	
	}
	
	if (*isfound) {
		writeLine("stdout", "System Collection found at *systemcoll");
	} else {

		msiCollCreate(*systemcoll, 1, *status);
		writeLine("stdout", "Created: *systemcoll");
	}

	*licenseColl = "/" ++ $rodsZoneClient ++ IILICENSECOLLECTION;
	if (!uuCollectionExists(*licenseColl)) {
		msiCollCreate(*licenseColl, 1, *status);
		writeLine("stdout", "Created: *licenseColl");
	}

	*licenseSrc = "*src/*license.txt";
	*licenseDst = "*licenseColl/*license.txt";
	if(!uuFileExists(*licenseDst)) {
		msiDataObjPut(*licenseDst, *resc, "localPath=*licenseSrc", *status);
		writeLine("stdout", "Installed *license");
		msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "license_url", *url);
		msiAssociateKeyValuePairsToObj(*kvp, *licenseDst, "-d");
	} else if (*force == 1) {
		msiDataObjPut(*licenseDst, *resc, "localPath=*licenseSrc++++forceFlag=", *status);
		writeLine("stdout", "Force installed *license");
		msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "license_url", *url);
		msiSetKeyValuePairsToObj(*kvp, *licenseDst, "-d");
	} else {
		writeLine("stdout", "*license already exists");
	}
	

}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/licenses", *license="", *url="", *force=0
output ruleExecOut
