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

	*xsdforxsd = *xsdcoll ++ "/" ++ "schema-for-xsd.xsd";
	msiDataObjPut(*xsdforxsd, *resc, "localPath=*src/schema-for-xsd.xsd++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xsdforxsd");

	*xsdforformelements = *xsdcoll ++ "/" ++ "schema-for-formelements.xsd";
	msiDataObjPut(*xsdforformelements, *resc, "localPath=*src/schema-for-formelements.xsd++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xsdforformelements");
	
	*xsddefault = *xsdcoll ++ "/" ++ IIXSDDEFAULTNAME;	
        if (uuFileExists(*xsddefault)) {
		msiDataObjPut(*xsddefault, *resc, "localPath=*src/*default.xsd++++forceFlag=", *status);
                writeLine("stdout", "Force Update: *xsddefault");
	} else {
		msiDataObjPut(*xsddefault, *resc, "localPath=*src/*default.xsd", *status);
		writeLine("stdout", "Created: *xsddefault");
	}

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
        if (uuFileExists(*xmldefault)) {
		msiDataObjPut(*xmldefault, *resc, "localPath=*src/*default.xml++++forceFlag=", *status);
		writeLine("stdout", "Force Update: *xmldefault");
        } else {
		msiDataObjPut(*xmldefault, *resc, "localPath=*src/*default.xml", *status);
		writeLine("stdout", "Created: *xmldefault");
	}	

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
        if (uuFileExists(*xsldefault)) {
		msiDataObjPut(*xsldefault, *resc, "localPath=*src/*default.xsl++++forceFlag=", *status)
                writeLine("stdout", "Force Update: *xsldefault");
	} else {
		msiDataObjPut(*xsldefault, *resc, "localPath=*src/*default.xsl", *status);
		writeLine("stdout", "Created: *xsldefault");
	}

        *xsldatacite = *xslcoll ++ "/" ++ IIDATACITEXSLDEFAULTNAME;
        if (uuFileExists(*xsldatacite)) {
		msiDataObjPut(*xsldatacite, *resc, "localPath=*src/*default"++"2datacite.xsl++++forceFlag=", *status);
 		writeLine("stdout", "Force Update: *xsldatacite");
 	} else {
		msiDataObjPut(*xsldatacite, *resc, "localPath=*src/*default"++"2datacite.xsl", *status);
		writeLine("stdout", "Created: *xsldatacite");
        }

        *xsllandingpage = *xslcoll ++ "/" ++ IILANDINGPAGEXSLDEFAULTNAME;
        if (uuFileExists(*xsllandingpage)) {
		msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/*default"++"2landingpage.xsl++++forceFlag=", *status);
 		writeLine("stdout", "Force Update: *xsllandingpage");
 	} else {
		msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/*default"++"2landingpage.xsl", *status);
		writeLine("stdout", "Created: *xsllandingpage");
        }

}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/xml", *default="ilab"
output ruleExecOut
