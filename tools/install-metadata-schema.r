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

	# Install system collection
	*isfound = false;
	*systemcoll = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *systemcoll) {
		*isfound = true;
	}

	if (*isfound) {
		writeLine("stdout", "System collection found at *systemcoll");
	} else {
		msiCollCreate(*systemcoll, 1, *status);
		writeLine("stdout", "Installed: *systemcoll");
	}

	# Install schemas collection
	*isfound = false;
	*schemasColl = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *schemasColl) {
		*isfound = true;
	}

	if(*isfound) {
		writeLine("stdout", "Schemas collection already exists at: *schemasColl");
	} else {
		msiCollCreate(*schemasColl, 1, *status);
		msiSetACL("default", "admin:read", "public", *schemasColl);
		msiSetACL("default", "admin:inherit", "public", *schemasColl);
		writeLine("stdout", "Installed: *schemasColl");
	}

	# Install schema collection
	*isfound = false;
	*schemaColl = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ *category;
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *schemaColl) {
		*isfound = true;
	}

	if(*isfound) {
		writeLine("stdout", "Schema collection already exists at: *schemaColl");
	} else {
		msiCollCreate(*schemaColl, 1, *status);
		msiSetACL("default", "admin:read", "public", *schemaColl);
		msiSetACL("default", "admin:inherit", "public", *schemaColl);
		writeLine("stdout", "Installed: *schemaColl");
	}

	# Install metadata JSON
	*jsondefault = *schemaColl ++ "/" ++ IIJSONNAME;
        *defaultJsonSchema = IIJSONNAME;
        if (uuFileExists(*jsondefault)) {
		if (*update == 1) {
			msiDataObjPut(*jsondefault, *resc, "localPath=*src/*schema/*defaultJsonSchema++++forceFlag=", *status);
			writeLine("stdout", "Updated: *jsondefault");
		} else {
			writeLine("stdout", "Present: *jsondefault");
		}
	} else {
		msiDataObjPut(*jsondefault, *resc, "localPath=*src/*schema/*defaultJsonSchema", *status);
		writeLine("stdout", "Installed: *jsondefault");
	}

	# Install metadata JSON UI schema
	*jsondefault = *schemaColl ++ "/" ++ IIJSONUINAME;
    *defaultJsonSchema = IIJSONUINAME;
    if (uuFileExists(*jsondefault)) {
		if (*update == 1) {
			msiDataObjPut(*jsondefault, *resc, "localPath=*src/*schema/*defaultJsonSchema++++forceFlag=", *status);
			writeLine("stdout", "Updated: *jsondefault");
		} else {
			writeLine("stdout", "Present: *jsondefault");
		}
	} else {
		msiDataObjPut(*jsondefault, *resc, "localPath=*src/*schema/*defaultJsonSchema", *status);
		writeLine("stdout", "Installed: *jsondefault");
	}
}

input *resc="irodsResc", *src="/etc/irods/yoda-ruleset/schemas/", *schema="default-1", *category="default", *update=0
output ruleExecOut
