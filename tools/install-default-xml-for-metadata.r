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
		writeLine("stdout", "Installed: *systemcoll");
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
		writeLine("stdout", "Installed: *xsdcoll");
	}

	*xsdforxsd = *xsdcoll ++ "/" ++ "schema-for-xsd.xsd";
	if (uuFileExists(*xsdforxsd)) {
		if (*update == 1) {
			msiDataObjPut(*xsdforxsd, *resc, "localPath=*src/xsd/schema-for-xsd.xsd++++forceFlag=", *status);
			writeLine("stdout", "Update: *xsdforxsd");
		} else {
			writeLine("stdout", "Present: *xsdforxsd");
		}
	} else {
		msiDataObjPut(*xsdforxsd, *resc, "localPath=*src/xsd/schema-for-xsd.xsd", *status);
		writeLine("stdout", "Installed: *xsdforxsd");
	}

	*xsdforformelements = *xsdcoll ++ "/" ++ "schema-for-formelements.xsd";
	msiDataObjPut(*xsdforformelements, *resc, "localPath=*src/xsd/schema-for-formelements.xsd++++forceFlag=", *status);
	writeLine("stdout", "Installed: *xsdforformelements");
	
	*xsddefault = *xsdcoll ++ "/" ++ IIXSDDEFAULTNAME;	
        if (uuFileExists(*xsddefault)) {
		if (*update == 1) {
			msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*default.xsd++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xsddefault");
		} else {
			writeLine("stdout", "Present: *xsddefault");
		}
	} else {
		msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*default.xsd", *status);
		writeLine("stdout", "Installed: *xsddefault");
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
		writeLine("stdout", "Installed: *xmlcoll");
	}

	*xmldefault = *xmlcoll ++ "/" ++ IIFORMELEMENTSDEFAULTNAME;	
        if (uuFileExists(*xmldefault)) {
		if (*update == 1) {
			msiDataObjPut(*xmldefault, *resc, "localPath=*src/formelements/*default.xml++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xmldefault");
		} else {
			writeLine("stdout", "Present: *xmldefault");
		}
        } else {
		msiDataObjPut(*xmldefault, *resc, "localPath=*src/formelements/*default.xml", *status);
		writeLine("stdout", "Installed: *xmldefault");
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
		writeLine("stdout", "Installed: *xslcoll");
	}

	*xsldefault = *xslcoll ++ "/" ++ IIXSLDEFAULTNAME;
        if (uuFileExists(*xsldefault)) {
		if (*update == 1) {
			msiDataObjPut(*xsldefault, *resc, "localPath=*src/xsl/*default.xsl++++forceFlag=", *status)
			writeLine("stdout", "Updated: *xsldefault");
		} else {
			writeLine("stdout", "Present: *xsldefault");
		}
	} else {
		msiDataObjPut(*xsldefault, *resc, "localPath=*src/xsl/*default.xsl", *status);
		writeLine("stdout", "Installed: *xsldefault");
	}

        *xsldatacite = *xslcoll ++ "/" ++ IIDATACITEXSLDEFAULTNAME;
        if (uuFileExists(*xsldatacite)) {
		if (*update == 1) {	
			msiDataObjPut(*xsldatacite, *resc, "localPath=*src/xsl/*default"++"2datacite.xsl++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xsldatacite");
		} else {
			writeLine("stdout", "Present: *xsldatacite");
		}
 	} else {
		msiDataObjPut(*xsldatacite, *resc, "localPath=*src/xsl/*default"++"2datacite.xsl", *status);
		writeLine("stdout", "Installed: *xsldatacite");
        }

        *xsllandingpage = *xslcoll ++ "/" ++ IILANDINGPAGEXSLDEFAULTNAME;
        if (uuFileExists(*xsllandingpage)) {
		if (*update == 1) {
			msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/xsl/*default"++"2landingpage.xsl++++forceFlag=", *status);
 			writeLine("stdout", "Updated: *xsllandingpage");
		} else {
			writeLine("stdout", "Present: *xsllandingpage");
		}
 	} else {
		msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/xsl/*default"++"2landingpage.xsl", *status);
		writeLine("stdout", "Installed: *xsllandingpage");
        }

        *xslemptylandingpage = *xslcoll ++ "/" ++ IIEMPTYLANDINGPAGEXSLNAME;
        if (uuFileExists(*xslemptylandingpage)) {
		if (*update == 1) {
			msiDataObjPut(*xslemptylandingpage, *resc, "localPath=*src/xsl/emptylandingpage.xsl++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xslemptylandingpage");
		} else {
			writeLine("stdout", "Present: *xslemptylandingpage");
		}
	} else {
		msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/xsl/emptylandingpage.xsl", *status);
		writeLine("stdout", "Installed: *xslemptylandingpage");
        }

}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/xml", *default="ilab", *update=0
output ruleExecOut
