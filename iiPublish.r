# \file iiPublish.r
# \brief This file contains rules related to publishing a datapackage
# 		for a research group
#
# \author Paul Frederiks
#
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiGenerateDataciteXml
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

# \brief iiGenerateCombiXml
iiGenerateCombiXml(*publicationConfig, *publicationState){
	
	*tempColl = "/" ++ $rodsZoneClient ++ IIPUBLICATIONCOLLECTION;
	*publicHost = *publicationConfig.publicHost;

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
	if (*publicationState.accessRestriction == "Open") {
	   *systemMetadata = *systemMetadata ++ 
           "    <Open_Access_Link><![CDATA[https://*publicHost/*subPath]]></Open_Access_Link>\n";
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

# \brief iiGetLastModifiedDate
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
	*lastModifiedDateTime = timestrf(datetime(int(*lastModifiedTimestamp)), "%Y-%m-%dT%H:%M:%S%z");
	*publicationState.lastModifiedDateTime = *lastModifiedDateTime;
	writeLine("serverLog", "iiGetLastModifiedDateTime: *lastModifiedDateTime");
}



# \brief iiGeneratePreliminaryDOI
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


# \brief iiPostMetadataToDataCite
iiPostMetadataToDataCite(*publicationConfig, *publicationState){ 
	*dataCiteUrl = "https://" ++ *publicationConfig.dataCiteServer ++ "/metadata";
	*dataCiteXmlPath = *publicationState.dataCiteXmlPath;
	*len = int(*publicationState.dataCiteXmlLen);
	msiDataObjOpen("objPath=*dataCiteXmlPath", *fd);
	msiDataObjRead(*fd, *len, *buf);
	msiDataObjClose(*fd, *status);
	msiBytesBufToStr(*buf, *dataCiteXml);
	msiRegisterDataCiteDOI(*dataCiteUrl, *publicationConfig.dataCiteUsername, *publicationConfig.dataCitePassword, *dataCiteXml, *httpCode);
	writeLine("serverLog", "iiPostMetadataToDataCite: HTTP CODE *httpCode");
}

# \brief iiMintDOI
iiMintDOI(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	*landingPageUrl = *publicationState.landingPageUrl;
	*dataCiteUrl = "https://" ++ *publicationConfig.dataCiteServer ++ "/doi";

	*request = "doi=*yodaDOI\nurl=*landingPageUrl\n";
	msiRegisterDataCiteDOI(*dataCiteUrl, *publicationConfig.dataCiteUsername, *publicationConfig.dataCitePassword, *request, *httpCode); 
	writeLine("serverLog", "iiMintDOI: HTTP CODE *httpCode");
}


# iiGenerateLandingPageUrl
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


# iiGenerateLandingPage
iiGenerateLandingPage(*publicationConfig, *publicationState) {
	writeLine("serverLog","Entered iiGenerateLandingPage");
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
		writeLine("serverLog", "iiGenerateDataCiteXml: failed to apply Xslt *dataCiteXslPath to *combiXmlPath. errorcode *err");
		*publicationState.status = "UNRECOVERABLE";
	} else {
		*landingPagePath = "*tempColl/*randomId.html";
 		msiDataObjCreate(*landingPagePath, "forceFlag=", *fd);
		msiDataObjWrite(*fd, *buf, *len);
		msiDataObjClose(*fd, *status);
		writeLine("serverLog", "landing page len=*len");
		*publicationState.landingPageLen = str(*len);
		*publicationState.landingPagePath = *landingPagePath;	
		writeLine("serverLog", "iiGenerateDataCiteXml: Generated *landingPagePath");
	}
}

# \brief iiCopyLandingPage2PublicHost
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
		*publicationState.status = "RETRY";
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


# \brief iiCopyYodaMetataToMOAI
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
		 "yodaInstance");
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
		 "yoda_instance");

	msiString2KeyValPair("randomIdLength=6%yodaInstance=" ++ UUINSTANCENAME, *publicationConfig);
	*sysColl = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;
	writeLine("serverLog", "iiGetPublicationConfig: fetching publication configuration from *sysColl");
	iiCollectionMetadataKvpList(*sysColl, UUORGMETADATAPREFIX, true, *kvpList);
	# Add all metadata keys found to publicationConfig with the configKey as key.
	foreach(*kvp in *kvpList) {
		for(*idx = 0;*idx < 10;*idx = *idx + 1) {
			if (*kvp.attrName == elem(*metadataAttributes, *idx)) {
				*configKey = elem(*configKeys, *idx);
				*publicationConfig."*configKey" = *kvp.attrValue;
				break;
			}
		}
	}
	# Check if all config keys are set;
	for(*idx = 0;*idx < 10;*idx = *idx + 1) {
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

iiGetPublicationState(*vaultPackage, *publicationState) {
	writeLine("serverLog", "iiGetPublicationState: fetching state of *vaultPackage");
	iiCollectionMetadataKvpList(*vaultPackage, UUORGMETADATAPREFIX++"publication_", true, *kvpList);
	foreach(*kvp in *kvpList) {
		*key = *kvp.attrName;
		*val = *kvp.attrValue;
		*publicationState."*key" = *val;
	}

	*publicationState.accessRestriction = "Closed";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME like '%Access_Restriction' AND COLL_NAME = *vaultPackage) {
		*publicationState.accessRestriction = *row.META_COLL_ATTR_VALUE;
	}
	*err = errorcode(msiGetValByKey(*publicationState, "status", *status));
	if (*err < 0) {
		*publicationState.status = "PROCESSING";
	}

	*publicationState.vaultPackage = *vaultPackage;
	writeKeyValPairs("serverLog", *publicationState, "=");
}

iiSavePublicationState(*vaultPackage, *publicationState) {
	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
		if (*val != "") {
			*attrName = UUORGMETADATAPREFIX ++ "publication_";
			*kvp."*attrName" = *val;
		}
	}
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

iiCheckDOIAvailability(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	*url = "https://" ++ *publicationConfig.dataCiteServer ++ "/doi/" ++ *yodaDOI;
	*username = *publicationConfig.dataCiteUsername;
	*password = *publicationConfig.dataCitePassword;
	writeLine("serverLog", "msiGetDataCiteDOI: *url, *username, *password");	
	msiGetDataCiteDOI(*url, *username, *password, *result, *httpCode);	
	if (*httpCode == "404") {
		# DOI is available!
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

iiHasKey(*kvp, *key) {
	*err = errorcode(*kvp."*key");
	if (*err == 0) {
		*result = true;
	} else {
		*result = false;
	}
	*result;
}

# \brief iiProcessPublication
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
	if (*status == "Unrecoverable") {
		succeed;
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
			*publicationState.status = "Retry";
			iiSavePublicationState(*vaultPackage, *publicationState);
			*status = "Retry";
			succeed;
		} else {
			iiSavePublicationState(*vaultPackage, *publicationState);
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteXmlPath")) {
		# Generate DataCite XML
		*err = errorcode(iiGenerateDataCiteXml(*publicationConfig, *publicationState));
	}

	# Check if DOI is in use
	iiCheckDOIAvailability(*publicationConfig, *publicationState);

	# Send DataCite XML to metadata end point
	iiPostMetadataToDataCite(*publicationConfig, *publicationState);
		
	# Create landing page
	iiGenerateLandingPage(*publicationConfig, *publicationState);
	
	# Create Landing page URL
	iiGenerateLandingPageUrl(*publicationConfig, *publicationState);
	
	# Use secure copy to push landing page to the public host
	iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState);
	
	# Use secure copy to push combi XML to MOAI server
	iiCopyMetadataToMOAI(*publicationConfig, *publicationState);

	# Mint DOI with landing page URL.
	iiMintDOI(*publicationConfig, *publicationState);

	*status = "OK";
	*publicationStatus = *status;	
	# Save state to metadata of vault package
	iiSavePublicationState(*vaultPackage, *publicationState);
}
