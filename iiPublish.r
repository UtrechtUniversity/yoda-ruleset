# \file iiPublish.r
# \brief This file contains rules related to publishing a datapackage
# 		for a research group
#
# \author Paul Frederiks
#
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiGenerateDataciteXml      Generate a dataCite compliant XML using XSLT
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is passed around as key-value-pairs 
iiGenerateDataCiteXml(*publicationConfig, *publicationState) {
	*combiXmlPath = *publicationState.combiXmlPath;
	*randomId = *publicationState.randomId;
	*vaultPackage = *publicationState.vaultPackage;
	uuChopPath(*combiXmlPath, *tempColl, *_);
	*dataCiteXmlPath = *tempColl ++ "/" ++ *randomId ++ "-dataCite.xml";

	*pathElems = split(*vaultPackage, "/");
	*rodsZone = elem(*pathElems, 0);
	*vaultGroup = elem(*pathElems, 2);
	uuGetBaseGroup(*vaultGroup, *baseGroup);
	uuGroupGetCategory(*baseGroup, *category, *subcategory);

	*dataCiteXslPath = "";
	*xslColl = "/"++*rodsZone++IIXSLCOLLECTION;
	*xslName = *category++"2datacite.xml";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		*dataCiteXslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*dataCiteXslPath == "") {
		*dataCiteXslPath = "/" ++ *rodsZone ++ IIXSLCOLLECTION ++ "/" ++ IIDATACITEXSLDEFAULTNAME;
	}

	*err = errorcode(msiXsltApply(*dataCiteXslPath, *combiXmlPath, *buf));
	if (*err < 0) {
		writeLine("serverLog", "iiGenerateDataCiteXml: failed to apply Xslt *dataCiteXslPath to *combiXmlPath. errorcode *err");
		*publicationState.status = "Unrecoverable";
	} else {
 		msiDataObjCreate(*dataCiteXmlPath, "forceFlag=", *fd);
		msiDataObjWrite(*fd, *buf, *len);
		msiDataObjClose(*fd, *status);
		*publicationState.dataCiteXmlPath = *dataCiteXmlPath;
		*publicationState.dataCiteXmlLen = str(*len);
		writeLine("serverLog", "iiGenerateDataCiteXml: Generated *dataCiteXmlPath");
	}
}

# \brief iiGenerateCombiXml         Join system metadata with the user metadata in yoda-metadata.xml 
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiGenerateCombiXml(*publicationConfig, *publicationState){
	
	*tempColl = "/" ++ $rodsZoneClient ++ IIPUBLICATIONCOLLECTION;
	*davrodsAnonymousVHost = *publicationConfig.davrodsAnonymousVHost;

	*vaultPackage = *publicationState.vaultPackage;
	*randomId = *publicationState.randomId;
	*yodaDOI = *publicationState.yodaDOI;
        *lastModifiedDateTime = *publicationState.lastModifiedDateTime;

	*subPath = triml(*vaultPackage, "/home/");
	msiGetIcatTime(*now, "unix");
	*publicationDate = uuiso8601date(*now);
	*combiXmlPath = "*tempColl/*randomId-combi.xml";
	*publicationState.combiXmlPath = *combiXmlPath;
	*systemMetadata =
	   "  <System>\n" ++
	   "    <Last_Modified_Date>*lastModifiedDateTime</Last_Modified_Date>\n" ++
	   "    <Persistent_Identifier_Datapackage>\n" ++ 
           "       <Identifier_Scheme>DOI</Identifier_Scheme>\n" ++
           "       <Identifier>*yodaDOI</Identifier>\n" ++ 
           "    </Persistent_Identifier_Datapackage>\n" ++
           "    <Publication_Date>*publicationDate</Publication_Date>\n";
	if (*publicationState.accessRestriction like "Open*") {
	   *systemMetadata = *systemMetadata ++ 
           "    <Open_Access_Link><![CDATA[https://*davrodsAnonymousVHost/*subPath]]></Open_Access_Link>\n";
	}
	*systemMetadata = *systemMetadata ++
           "    <License_URL><![CDATA[http://tobedetermined]]></License_URL>\n" ++
           "  </System>\n" ++ 
           "</metadata>";

	iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath);

	msiDataObjCopy(*metadataXmlPath, *combiXmlPath, "forceFlag=", *status);
	msiDataObjOpen("objPath=*combiXmlPath++++openFlags=O_RDWR", *fd);
	msiDataObjLseek(*fd, -12, "SEEK_END", *status);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);
	writeLine("serverLog", "iiGenerateCombiXml: generated *combiXmlPath");

}

# \brief iiGetLastModifiedDate      Determine the time of last modification as a datetime with UTC offset 
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiGetLastModifiedDateTime(*publicationState) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";
	*vaultPackage = *publicationState.vaultPackage;
	foreach(*row in SELECT order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE
                                          WHERE META_COLL_ATTR_NAME = *actionLog
                                          AND COLL_NAME = *vaultPackage) {
		*logRecord = *row.META_COLL_ATTR_VALUE;
		break;
	}

	*lastModifiedTimestamp = "";
	msi_json_arrayops(*logRecord, *lastModifiedTimestamp, "get", 0);
	# iso8601 compliant datetime with UTC offset
	*lastModifiedDateTime = timestrf(datetime(int(*lastModifiedTimestamp)), "%Y-%m-%dT%H:%M:%S%z");
	*publicationState.lastModifiedDateTime = *lastModifiedDateTime;
	writeLine("serverLog", "iiGetLastModifiedDateTime: *lastModifiedDateTime");
}



# \brief iiGeneratePreliminaryDOI   Generate a Preliminary DOI. Preliminary, because we check for collision later.
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiGeneratePreliminaryDOI(*publicationConfig, *publicationState) {
	*dataCitePrefix = *publicationConfig.dataCitePrefix;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*length = int(*publicationConfig.randomIdLength);
	msiGenerateRandomID(*length, *randomId);
	*yodaDOI = "*dataCitePrefix/*yodaPrefix-*randomId";
	*publicationState.randomId = *randomId;
	*publicationState.yodaDOI = *yodaDOI;
	writeLine("serverLog", "iiGeneratePreliminaryDOI: *yodaDOI");
}


# \brief iiPostMetadataToDataCite   Upload dataCite XML to dataCite. This will register the DOI, without minting it.
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiPostMetadataToDataCite(*publicationConfig, *publicationState){ 
	*dataCiteUrl = "https://" ++ *publicationConfig.dataCiteServer ++ "/metadata";
	*dataCiteXmlPath = *publicationState.dataCiteXmlPath;
	*len = int(*publicationState.dataCiteXmlLen);
	msiDataObjOpen("objPath=*dataCiteXmlPath", *fd);
	msiDataObjRead(*fd, *len, *buf);
	msiDataObjClose(*fd, *status);
	msiBytesBufToStr(*buf, *dataCiteXml);
	msiRegisterDataCiteDOI(*dataCiteUrl, *publicationConfig.dataCiteUsername, *publicationConfig.dataCitePassword, *dataCiteXml, *httpCode);
	if (*httpCode == "201") {
		*publicationState.dataCiteMetadataPosted = "yes";
		succeed;
	} else if (*httpCode == "400") {
		# invalid XML
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiPostMetadataToDataCite: 400 Bad Request - Invalid XML, wrong prefix");
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "500") {
		*publicationState.status = "Retry";
		writeLine("serverLog", "iiPostMetadataToDataCite: *httpCode received. Could be retried later");
	}

}

# \brief iiMintDOI                  Announce the landing page URL for a DOI to dataCite. This will mint the DOI.
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiMintDOI(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	*landingPageUrl = *publicationState.landingPageUrl;
	*dataCiteUrl = "https://" ++ *publicationConfig.dataCiteServer ++ "/doi";

	*request = "doi=*yodaDOI\nurl=*landingPageUrl\n";
	msiRegisterDataCiteDOI(*dataCiteUrl, *publicationConfig.dataCiteUsername, *publicationConfig.dataCitePassword, *request, *httpCode); 
	writeLine("serverLog", "iiMintDOI: *httpCode");
	if (*httpCode == "201") {
		*publicationState.DOIMinted = "yes";
		succeed;
	} else if (*httpCode == "400") {
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiMintDOI: 400 Bad Request - request body must be exactly two lines: DOI and URL; wrong domain, wrong prefix");
		succeed;
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "412" || *httpCode == "500") {
		*publicationState.status = "Retry";
		writeLine("serverLog", "iiMintDOI: *httpCode received. Could be retried later");
		succeed;
	}
}


# iiGenerateLandingPageUrl          Generate a URL for the landing page
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiGenerateLandingPageUrl(*publicationConfig, *publicationState) {
	*vaultPackage = *publicationState.vaultPackage;
	*yodaDOI = *publicationState.yodaDOI;
	*publicVHost = *publicationConfig.publicVHost;
	*yodaInstance = *publicationConfig.yodaInstance;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*randomId = *publicationState.randomId;
	*publicPath = "*yodaInstance/*yodaPrefix/*randomId.html";
	*landingPageUrl = "https://*publicVHost/*publicPath";	
	*publicationState.landingPageUrl = *landingPageUrl;
	writeLine("serverLog", "iiGenerateLandingPageUrl: *landingPageUrl");
}


# iiGenerateLandingPage             Generate a Landing page from the combi XML using XSLT 
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiGenerateLandingPage(*publicationConfig, *publicationState) {
	*combiXmlPath = *publicationState.combiXmlPath;
	uuChopPath(*combiXmlPath, *tempColl, *_);
	*randomId = *publicationState.randomId;
	*pathElems = split(*combiXmlPath, "/");
	*rodsZone = elem(*pathElems, 0);
	*vaultGroup = elem(*pathElems, 2);
	uuGetBaseGroup(*vaultGroup, *baseGroup);
	uuGroupGetCategory(*baseGroup, *category, *subcategory);

	*landingPageXslPath = "";
	*xslColl = "/"++*rodsZone++IIXSLCOLLECTION;
	*xslName = *category++"2landingpage.xml";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		*landingPageXslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*landingPageXslPath == "") {
		*landingPageXslPath = "/" ++ *rodsZone ++ IIXSLCOLLECTION ++ "/" ++ IILANDINGPAGEXSLDEFAULTNAME;
	}
	*err = errorcode(msiXsltApply(*landingPageXslPath, *combiXmlPath, *buf));
	if (*err < 0) {
		writeLine("serverLog", "iiGenerateLandingPage: failed to apply Xslt *landingPageXslPath to *combiXmlPath. errorcode *err");
		*publicationState.status = "Unrecoverable";
	} else {
		*landingPagePath = "*tempColl/*randomId.html";
 		msiDataObjCreate(*landingPagePath, "forceFlag=", *fd);
		msiDataObjWrite(*fd, *buf, *len);
		msiDataObjClose(*fd, *status);
		writeLine("serverLog", "landing page len=*len");
		*publicationState.landingPageLen = str(*len);
		*publicationState.landingPagePath = *landingPagePath;	
		writeLine("serverLog", "iiGenerateLandingPage: Generated *landingPagePath");
	}
}

# \brief iiCopyLandingPage2PublicHost
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState) {
	*publicHost = *publicationConfig.publicHost;
	*landingPagePath = *publicationState.landingPagePath;
	*yodaInstance = *publicationConfig.yodaInstance;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*randomId =  *publicationState.randomId;
	*publicPath = "*yodaInstance/*yodaPrefix/*randomId.html";
	*argv = "*publicHost inbox /var/www/landingpages/*publicPath";
	*err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *landingPagePath, 1, *cmdExecOut));
	if (*err < 0) {
		*publicationState.status = "Retry";
		msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
		msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
		writeLine("serverLog", "iiCopyLandingPage2PublicHost: errorcode *err");
		writeLine("serverLog", *stderr);
		writeLine("serverLog", *stdout);
	} else {
		*publicationState.landingPageUploaded = "yes";
		writeLine("serverLog", "iiCopyLandingPage2PublicHost: pushed *publicPath");
	}
}


# \brief iiCopyYodaMetataToMOAI     Use secure copy to push the combi XML to MOAI
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs 
iiCopyMetadataToMOAI(*publicationConfig, *publicationState) {
	*publicHost = *publicationConfig.publicHost;
	*yodaInstance = *publicationConfig.yodaInstance;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*randomId = *publicationState.randomId;
	*combiXmlPath = *publicationState.combiXmlPath;
	*argv = "*publicHost inbox /var/www/moai/metadata/*yodaInstance/*yodaPrefix/*randomId.xml"
	*err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *combiXmlPath, 1, *cmdExecOut));
	if (*err < 0) {
		msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
		msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
		writeLine("serverLog", "iiCopyMetadataToMoai: errorcode *err");
		writeLine("serverLog", *stderr);
		writeLine("serverLog", *stdout);
	} else {
		*publicationState.oaiUploaded = "yes";
		writeLine("serverLog", "iiCopyMetadataToMOAI: pushed *combiXmlPath");
	}

}

# \brief iiSetAccessRestriction     Set access restriction for vault package.
# \param[in] vaultPackage           Path to the package in the vault
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
iiSetAccessRestriction(*vaultPackage, *publicationState) {
        *accessRestriction = *publicationState.accessRestriction;

	*accessLevel = "null";
	if (*publicationState.accessRestriction like "Open*") {
	   *accessLevel = "read";
	}

	*err = errorcode(msiSetACL("recursive", *accessLevel, "anonymous", *vaultPackage));
	if (*err < 0) {
		*publicationState.anonymousAccessLevel = *accessLevel;
		writeLine("serverLog", "iiSetAccessRestriction: errorcode *err");
	} else {
		writeLine("serverLog", "iiSetAccessRestriction: anonymous access level *accessLevel");
	}
}

# iiGetPublicationConfig         Configuration is extracted from metadata on the UUSYSTEMCOLLECTION
# \param[out] publicationConfig  a key-value-pair containing the configuration
iiGetPublicationConfig(*publicationConfig) {
	# Translation from camelCase config key to snake_case metadata attribute
	*configKeys = list(
		 "dataCiteUsername",
 		 "dataCitePassword",
		 "dataCiteServer",
		 "publicHost",
		 "publicVHost",
		 "moaiHost",
		 "yodaPrefix",
		 "dataCitePrefix",
		 "randomIdLength",
		 "yodaInstance",
		 "davrodsAnonymousVHost"
		 );
	*metadataAttributes = list(
		 "datacite_username",
		 "datacite_password",
		 "datacite_server",
		 "public_host",
		 "public_vhost",
		 "moai_host",
		 "yoda_prefix",
		 "datacite_prefix",
		 "random_id_length",
		 "yoda_instance",
		 "davrods_anonymous_vhost");
	
	*nKeys = size(*configKeys);

	msiString2KeyValPair("randomIdLength=6%yodaInstance=" ++ UUINSTANCENAME, *publicationConfig);
	*sysColl = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	writeLine("serverLog", "iiGetPublicationConfig: fetching publication configuration from *sysColl");
	iiCollectionMetadataKvpList(*sysColl, UUORGMETADATAPREFIX, true, *kvpList);
	# Add all metadata keys found to publicationConfig with the configKey as key.
	foreach(*kvp in *kvpList) {
		for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
			if (*kvp.attrName == elem(*metadataAttributes, *idx)) {
				*configKey = elem(*configKeys, *idx);
				*publicationConfig."*configKey" = *kvp.attrValue;
				break;
			}
		}
	}
	# Check if all config keys are set;
	for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
		*configKey = elem(*configKeys, *idx);
		*err = errorcode(*publicationConfig."*configKey");
		if (*err < 0) {
			*metadataAttribute = elem(*metadataAttributes, *idx);
			writeLine("serverLog", "iiGetPublicationConfig: *configKey missing; please set *metadataAttribute on *sysColl");
			fail;
		}
	}
	writeKeyValPairs("serverLog", *publicationConfig, "=");
}

# \brief iiGetPublicationState   The publication state is kept as metadata on the vaultPackage
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
iiGetPublicationState(*vaultPackage, *publicationState) {
	# defaults
	*publicationState.status = "Unknown";
	*publicationState.accessRestriction = "Closed";

	iiCollectionMetadataKvpList(*vaultPackage, UUORGMETADATAPREFIX++"publication_", true, *kvpList);
	foreach(*kvp in *kvpList) {
		*key = *kvp.attrName;
		*val = *kvp.attrValue;
		*publicationState."*key" = *val;
	}

	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = *vaultPackage) {
		*publicationState.accessRestriction = *row.META_COLL_ATTR_VALUE;
	}
	*publicationState.vaultPackage = *vaultPackage;
	writeKeyValPairs("serverLog", *publicationState, "=");
}

# \brief iiSavePublicationState  Save the publicationState key-value-pair to AVU's on the vaultPackage
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
iiSavePublicationState(*vaultPackage, *publicationState) {
	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
		if (*val != "") {
			*attrName = UUORGMETADATAPREFIX ++ "publication_" ++ *key;
			*kvp."*attrName" = *val;
		}
	}
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

# iiCheckDOIAvailability            Request DOI to check on availibity. We want a 404 as return code
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pair 
iiCheckDOIAvailability(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	*url = "https://" ++ *publicationConfig.dataCiteServer ++ "/doi/" ++ *yodaDOI;
	*username = *publicationConfig.dataCiteUsername;
	*password = *publicationConfig.dataCitePassword;
	writeLine("serverLog", "msiGetDataCiteDOI: *url, *username, *password");	
	msiGetDataCiteDOI(*url, *username, *password, *result, *httpCode);	
	if (*httpCode == "404") {
		# DOI is available!
		*publicationState.DOIAvailable = "yes";
		succeed;
	} else if (*httpCode == "500" || *httpCode == "403" || *httpCode == "401") {
		# request failed, worth a retry
		*publicationState.status = "Retry";
	} else if (*httpCode == "200" || *httpCode == "204") {
		# DOI already in use. Scrub doi for retry.
		writeLine("stdout", "DOI *yodaDOI already in use.\n*result");
		*publicationState.yodaDOI = "";
		*publicationState.randomId = "";
		*publicationState.status = "Retry";
	}
}


# Helper function with use outside this ruleset. Move to UU ruleset
iiHasKey(*kvp, *key) {
	*err = errorcode(*kvp."*key");
	if (*err == 0) {
		*result = true;
	} else {
		*result = false;
	}
	*result;
}

# \brief iiProcessPublication   Routine to process a publication with sanity checks at every step
# \param[in] vaultPackage       path to package in the vault to publish
# \param[out] status		status of the publication
iiProcessPublication(*vaultPackage, *status) {
	*status = "Unknown";
	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != APPROVED_FOR_PUBLICATION) {
		*status = "NotAllowed";
		succeed;
	}

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		*status = "NotAllowed" ;
		succeed;
	}

	# Load configuration
	*err = errorcode(iiGetPublicationConfig(*publicationConfig));
	if (*err < 0) {
		*status = "Retry";
		succeed;
	}

	# Load state 
	iiGetPublicationState(*vaultPackage, *publicationState);
	*status = *publicationState.status;
	if (*status == "Unrecoverable" || *status == "Processing") {
		succeed;
	} else if (*status == "Unknown" || *status == "Retry") {
		*status = "Processing";
		*publicationState.status = "Processing";
	}
	

	if (!iiHasKey(*publicationState, "yodaDOI")) {
		# Generate Yoda DOI
		iiGeneratePreliminaryDOI(*publicationConfig, *publicationState);
		iiSavePublicationState(*vaultPackage, *publicationState);
	}

	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);
	
	
	if (!iiHasKey(*publicationState, "combiXmlPath")) {
		# Generate Combi XML consisting of user and system metadata
		*err = errorcode(iiGenerateCombiXml(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteXmlPath")) {
		# Generate DataCite XML
		*err = errorcode(iiGenerateDataCiteXml(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
		
	}

	if (!iiHasKey(*publicationState, "DOIAvailable")) {
		# Check if DOI is in use
		*err = errorcode(iiCheckDOIAvailability(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationStatus.status = "Retry";
		}
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteMetadataPosted")) {
		# Send DataCite XML to metadata end point
		*err = errorcode(iiPostMetadataToDataCite(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry" || *publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}		
	}
	
	# Create landing page
	if (!iiHasKey(*publicationState, "landingPagePath")) {
		*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}
	}
	
	# Create Landing page URL
	iiGenerateLandingPageUrl(*publicationConfig, *publicationState);
	
	if(!iiHasKey(*publicationState, "landingPageUploaded")) {
		# Use secure copy to push landing page to the public host
		*err = errorcode(iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}	
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}
	
	if(!iiHasKey(*publicationState, "oaiUploaded")) {
		# Use secure copy to push combi XML to MOAI server
		*err = errorcode(iiCopyMetadataToMOAI(*publicationConfig, *publicationState));
		if (*err < 0) {
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "anonymousAccessLevel")) {
		# Set access restriction for vault package.
		*err = errorcode(iiSetAccessRestriction(*vaultPackage, *publicationState));
		if (*err < 0) {
			writeLine("stdout", "iiSetAccessRestriction: *err");
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}
	
	if (!iiHasKey(*publicationState, "DOIMinted")) {
		# Mint DOI with landing page URL.
		*err = errorcode(iiMintDOI(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		#iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
			
		} else {
			writeLine("serverLog", "iiProcessPublication: All steps for publication completed");
			# The publication was a success;
			*publicationState.status = "OK";
			iiSavePublicationState(*vaultPackage, *publicationState);
			*status = *publicationState.status;	
			msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_status=" ++ PUBLISHED, *vaultStatusKvp);	
			msiSetKeyValuePairsToObj(*vaultStatusKvp, *vaultPackage, "-C");
		}
	}
}
