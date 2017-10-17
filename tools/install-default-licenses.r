installDefaultLicenses {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*isfound = false;
	*systemcoll = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *systemcoll) {
		*isfound = true;	
	}
	
	*isfound = false;
	foreach(*row in SELECT RESC_NAME WHERE RESC_NAME = *resc) {
		*isfound = true;
	}

	if (!*isfound) {
		writeLine("stdout", "Resource *resc is not found. Please provide a valid resource example:");
		writeLine("stdout", "irule -F ./install-default-xml-for-metadata.r '\*resc=\"demoResc\"'");
		failmsg(-1, "Aborting. Resource not found");
	}

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
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

	*licenses = IIDEFAULTLICENSES;
	foreach(*license in *licenses) {
		*licenseSrc = "*src/*license.txt";
		*licenseDst = "*licenseColl/*license.txt";
		if(!uuFileExists(*licenseDst)) {
			msiDataObjPut(*licenseDst, *resc, "localPath=*licenseSrc", *status);
			writeLine("stdout", "Installed *license");
		} else if (*force == 1) {
			msiDataObjPut(*licenseDst, *resc, "localPath=*licenseSrc++++forceFlag=", *status);
			writeLine("stdout", "Installed *license");

		}
	}

}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/licenses", *force=0
output ruleExecOut
