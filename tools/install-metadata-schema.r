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

    # Install schema for XSD
	*xsdforxsd = *schemasColl ++ "/" ++ "schema-for-xsd.xsd";
	if (uuFileExists(*xsdforxsd)) {
		if (*update == 1) {
			msiDataObjPut(*xsdforxsd, *resc, "localPath=*src/schema-for-xsd.xsd++++forceFlag=", *status);
			writeLine("stdout", "Update: *xsdforxsd");
		} else {
			writeLine("stdout", "Present: *xsdforxsd");
		}
	} else {
		msiDataObjPut(*xsdforxsd, *resc, "localPath=*src/schema-for-xsd.xsd", *status);
		writeLine("stdout", "Installed: *xsdforxsd");
	}


        # Install emtpy landingpage XSL (Yoda metadata XML to landingpage HTML)
        *xslemptylandingpage = *schemasColl ++ "/" ++ IIEMPTYLANDINGPAGEXSLNAME;
	*xsl = IIEMPTYLANDINGPAGEXSLNAME;
        if (uuFileExists(*xslemptylandingpage)) {
		if (*update == 1) {
			msiDataObjPut(*xslemptylandingpage, *resc, "localPath=*src/*xsl++++forceFlag=", *status);
			writeLine("stdout", "Updated: *xslemptylandingpage");
		} else {
			writeLine("stdout", "Present: *xslemptylandingpage");
		}
	} else {
		msiDataObjPut(*xslemptylandingpage, *resc, "localPath=*src/*xsl", *status);
		writeLine("stdout", "Installed: *xslemptylandingpage");
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

    if (*schema == "default-0") {
	    # Install research XSD
	    *xsddefault = *schemaColl ++ "/" ++ IIRESEARCHXSDNAME;
        *defaultResearchSchema = IIRESEARCHXSDNAME;
        if (uuFileExists(*xsddefault)) {
	    	if (*update == 1) {
	    		msiDataObjPut(*xsddefault, *resc, "localPath=*src/*schema/*defaultResearchSchema++++forceFlag=", *status);
		    	writeLine("stdout", "Updated: *xsddefault");
		    } else {
	    		writeLine("stdout", "Present: *xsddefault");
	    	}
	    } else {
		    writeLine("stdout", "Installed: *xsddefault");
	    }

	    # Install vault XSD
	    *xsddefault = *schemaColl ++ "/" ++ IIVAULTXSDNAME;
        *defaultVaultSchema = IIVAULTXSDNAME;
        if (uuFileExists(*xsddefault)) {
		    if (*update == 1) {
			    msiDataObjPut(*xsddefault, *resc, "localPath=*src/*schema/*defaultVaultSchema++++forceFlag=", *status);
     			writeLine("stdout", "Updated: *xsddefault");
		    } else {
			    writeLine("stdout", "Present: *xsddefault");
		    }
    	} else {
	    	msiDataObjPut(*xsddefault, *resc, "localPath=*src/*schema/*defaultVaultSchema", *status);
		    writeLine("stdout", "Installed: *xsddefault");
	    }

    	# Install AVU XSL (Yoda metadata XML to AVU XML)
	    *xsldefault = *schemaColl ++ "/" ++ IIAVUXSLNAME;
	    *xsl = IIAVUXSLNAME;
        if (uuFileExists(*xsldefault)) {
		    if (*update == 1) {
			    msiDataObjPut(*xsldefault, *resc, "localPath=*src/*schema/*xsl++++forceFlag=", *status)
	    		writeLine("stdout", "Updated: *xsldefault");
	    	} else {
		    	writeLine("stdout", "Present: *xsldefault");
		    }
    	} else {
	    	msiDataObjPut(*xsldefault, *resc, "localPath=*src/*schema/*xsl", *status);
		    writeLine("stdout", "Installed: *xsldefault");
    	}

	    # Install DataCite XSL (Yoda metadata XML to DataCite XML)
        *xsldatacite = *schemaColl ++ "/" ++ IIDATACITEXSLNAME;
	    *xsl = IIDATACITEXSLNAME;
        if (uuFileExists(*xsldatacite)) {
		    if (*update == 1) {
	    		msiDataObjPut(*xsldatacite, *resc, "localPath=*src/*schema/*xsl++++forceFlag=", *status);
		    	writeLine("stdout", "Updated: *xsldatacite");
    		} else {
	    		writeLine("stdout", "Present: *xsldatacite");
	    	}
 	    } else {
		    msiDataObjPut(*xsldatacite, *resc, "localPath=*src/*schema/*xsl", *status);
	    	writeLine("stdout", "Installed: *xsldatacite");
        }

        # Install landingpage XSL (Yoda metadata XML to landingpage HTML)
        *xsllandingpage = *schemaColl ++ "/" ++ IILANDINGPAGEXSLNAME;
	    *xsl = IILANDINGPAGEXSLNAME;
        if (uuFileExists(*xsllandingpage)) {
		    if (*update == 1) {
	    		msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/*schema/*xsl++++forceFlag=", *status);
 		    	writeLine("stdout", "Updated: *xsllandingpage");
	    	} else {
		    	writeLine("stdout", "Present: *xsllandingpage");
    		}
 	    } else {
		    msiDataObjPut(*xsllandingpage, *resc, "localPath=*src/*schema/*xsl", *status);
		    writeLine("stdout", "Installed: *xsllandingpage");
        }
	}

        # TRANSFORMATION

        # 1. Install transformations collection
        *isfound = false;
        *transformationsColl = "/" ++ $rodsZoneClient ++ IITRANSFORMATIONCOLLECTION;
        foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *transformationsColl) {
                *isfound = true;
        }

        if(*isfound) {
                writeLine("stdout", "Transformations collection already exists at: *transformationsColl");
        } else {
                msiCollCreate(*transformationsColl, 1, *status);
                msiSetACL("default", "admin:read", "public", *transformationsColl);
                msiSetACL("default", "admin:inherit", "public", *transformationsColl);
                writeLine("stdout", "Installed: *transformationsColl");
        }

        # 2. Install transformations collection
        *isfound = false;
        *transformationColl = "/" ++ $rodsZoneClient ++ IITRANSFORMATIONCOLLECTION ++ "/" ++ *schema;
        foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *transformationColl) {
                *isfound = true;
        }

        if(*isfound) {
                writeLine("stdout", "Transformation collection already exists at: *transformationColl");
        } else {
                msiCollCreate(*transformationColl, 1, *status);
                msiSetACL("default", "admin:read", "public", *transformationColl);
                msiSetACL("default", "admin:inherit", "public", *transformationColl);
                writeLine("stdout", "Installed: *transformationColl");
        }

        # 3. Install research transformation XSLs.
        *transXsl = *transformationColl ++ "/" ++ 'default-0-research.xsl';
        *localPath = *src ++ '../transformations/default-1/default-0-research.xsl';

        if (uuFileExists(*transXsl)) {
                if (*update == 1) {
                        msiDataObjPut(*transXsl, *resc, "localPath=*localPath++++forceFlag=", *status);
                        writeLine("stdout", "Updated: *transXsl");
                } else {
                        writeLine("stdout", "Present: *transXsl");
                }
        } else {
                msiDataObjPut(*transXsl, *resc, "localPath=*localPath", *status);
                writeLine("stdout", "Installed: *transXsl");
        }

        # 4. Install vault transformation XSLs.
        *transXsl = *transformationColl ++ "/" ++ 'default-0-vault.xsl';
        *localPath = *src ++ '../transformations/default-1/default-0-vault.xsl';

        if (uuFileExists(*transXsl)) {
                if (*update == 1) {
                        msiDataObjPut(*transXsl, *resc, "localPath=*localPath++++forceFlag=", *status);
                        writeLine("stdout", "Updated: *transXsl");
                } else {
                        writeLine("stdout", "Present: *transXsl");
                }
        } else {
                msiDataObjPut(*transXsl, *resc, "localPath=*localPath", *status);
                writeLine("stdout", "Installed: *transXsl");
        }

        # 5. Install transformation descriptions.
        *transTxt = *transformationColl ++ "/" ++ 'default-0.html';
        *localPath = *src ++ '../transformations/default-1/default-0.html';

        if (uuFileExists(*transTxt)) {
                if (*update == 1) {
                        msiDataObjPut(*transTxt, *resc, "localPath=*localPath++++forceFlag=", *status);
                        writeLine("stdout", "Updated: *transTxt");
                } else {
                        writeLine("stdout", "Present: *transTxt");
                }
        } else {
                msiDataObjPut(*transTxt, *resc, "localPath=*localPath", *status);
                writeLine("stdout", "Installed: *transTxt");
        }
}

input *resc="irodsResc", *src="/etc/irods/irods-ruleset-research/tools/schemas", *schema="default-0", *category="default", *update=0
output ruleExecOut
