createXmlXsdCollections {
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
		writeLine("stdout", "Created: *xsdcoll");
	}

	
	*xsddefault = *xsdcoll ++ "/" ++ IIXSDDEFAULTNAME;	
	msiDataObjPut(*xsddefault, *resc, "localPath=*src/default.xsd++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xsddefault");

	*isfound = false;
	*xmlcoll = "/" ++ $rodsZoneClient ++ IIFORMELEMENTSCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *xmlcoll) {
		*isfound = true;
	}
	if(*isfound) {
		writeLine("stdout", "System collection already exists at: *xmlcoll");
	} else {
		msiCollCreate(*xmlcoll, 1, *status);
		msiSetACL("default", "read", "public", *xmlcoll);
		msiSetACL("default", "admin:inherit", "public", *xmlcoll);
		writeLine("stdout", "Created: *xmlcoll");
	}

	*xmldefault = *xmlcoll ++ "/" ++ IIFORMELEMENTSDEFAULTNAME;	
	msiDataObjPut(*xmldefault, *resc, "localPath=*src/formelements.xml++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xmldefault");

        *isfound = false;
	*xslcoll = "/" ++ $rodsZoneClient ++ IIXSLCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *xslcoll) {
		*isfound = true;
	}
	if(*isfound) {
		writeLine("stdout", "System collection already exists at *xslcoll");
	} else {
		msiCollCreate(*xslcoll, 1, *status);
		msiSetACL("default", "read", "public", *xslcoll);
		msiSetACL("default", "admin:inherit", "public", *xslcoll);
		writeLine("stdout", "Created: *xslcoll");
	}

	*xsldefault = *xslcoll ++ "/" ++ IIXSLDEFAULTNAME;
	msiDataObjPut(*xsldefault, *resc, "localPath=*src/metadata.xsl++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xsldefault");

}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-ilab/tools/xml"
output ruleExecOut
