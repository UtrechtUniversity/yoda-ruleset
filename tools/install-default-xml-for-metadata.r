createXmlXsdCollections {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin.");
	}

	*isfound = false;
	foreach(*row in SELECT RESC_NAME WHERE RESC_NAME = *resc) {
		*isfound = true;
	}

	if (!*isfound) {
		writeLine("stdout", "Resource *resc is not found. Please provide a valid resource example:");
		writeLine("stdout", "irule -F ./install-default-xml-for-metadata.r '\*resc=\"irodsResc\"'");
		failmsg(-1, "Aborting. Resource not found");
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

        # Install schema for XSD
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

	# Install default research XSD
	*xsddefault = *xsdcoll ++ "/" ++ IIRESEARCHXSDDEFAULTNAME;
        *defaultResearchSchema = *default ++ "_research.xsd"
        if (uuFileExists(*xsddefault)) {
		if (*update == 1) {
			msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*defaultResearchSchema++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xsddefault");
		} else {
			writeLine("stdout", "Present: *xsddefault");
		}
	} else {
		msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*defaultResearchSchema.xsd", *status);
		writeLine("stdout", "Installed: *xsddefault");
	}

	# Install default vault XSD
	*xsddefault = *xsdcoll ++ "/" ++ IIVAULTXSDDEFAULTNAME;
        *defaultVaultSchema = *default ++ "_vault.xsd"
        if (uuFileExists(*xsddefault)) {
		if (*update == 1) {
			msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*defaultVaultSchema++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xsddefault");
		} else {
			writeLine("stdout", "Present: *xsddefault");
		}
	} else {
		msiDataObjPut(*xsddefault, *resc, "localPath=*src/xsd/*defaultVaultSchema.xsd", *status);
		writeLine("stdout", "Installed: *xsddefault");
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

	# Install default XSL (Yoda metadata XML to AVU XML)
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

	# Install DataCite XSL (Yoda metadata XML to DataCite XML)
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

        # Install landingpage XSL (Yoda metadata XML to landingpage HTML)
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

        # Install emtpy landingpage XSL (Yoda metadata XML to landingpage HTML)
        *xslemptylandingpage = *xslcoll ++ "/" ++ IIEMPTYLANDINGPAGEXSLNAME;
        if (uuFileExists(*xslemptylandingpage)) {
		if (*update == 1) {
			msiDataObjPut(*xslemptylandingpage, *resc, "localPath=*src/xsl/emptylandingpage.xsl++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xslemptylandingpage");
		} else {
			writeLine("stdout", "Present: *xslemptylandingpage");
		}
	} else {
		msiDataObjPut(*xslemptylandingpage, *resc, "localPath=*src/xsl/emptylandingpage.xsl", *status);
		writeLine("stdout", "Installed: *xslemptylandingpage");
        }
}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/xml", *default="default", *update=0
output ruleExecOut
