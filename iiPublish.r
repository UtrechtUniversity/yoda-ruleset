# \file      iiPublish.r
# \brief     This file contains rules related to publishing a datapackage
#            for a research group.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Generate a dataCite compliant XML using XSLT.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is passed around as key-value-pairs
#
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
	*xslColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
	*xslName = IIDATACITEXSLNAME;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		*dataCiteXslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*dataCiteXslPath == "") {
		*dataCiteXslPath = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IIDATACITEXSLNAME;
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
		#DEBUG writeLine("serverLog", "iiGenerateDataCiteXml: Generated *dataCiteXmlPath");
	}
}

# \brief Join system metadata with the user metadata in yoda-metadata.xml.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
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
	if (iiHasKey(*publicationState, "licenseUri")) {
    	   *systemMetadata = *systemMetadata ++
           "    <License_URI><![CDATA[" ++ *publicationState.licenseUri ++ "]]></License_URI>\n";
	}
	*systemMetadata = *systemMetadata ++
           "  </System>\n" ++
           "</metadata>";

	iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath, *metadataXmlSize);

	msiDataObjOpen("objPath=*metadataXmlPath", *fd);
	msiDataObjRead(*fd, *metadataXmlSize - 12, *buf);
	msiDataObjClose(*fd, *status);
	msiDataObjCreate(*combiXmlPath, "forceFlag=", *fd);
	msiDataObjWrite(*fd, *buf, *lenOut);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);
	#DEBUG writeLine("serverLog", "iiGenerateCombiXml: generated *combiXmlPath");
	*publicationState.combiXmlPath = *combiXmlPath;

}

# \brief Overwrite combi metadata with system-only metadata.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGenerateSystemXml(*publicationConfig, *publicationState) {
	*tempColl = "/" ++ $rodsZoneClient ++ IIPUBLICATIONCOLLECTION;
	*davrodsAnonymousVHost = *publicationConfig.davrodsAnonymousVHost;

	*vaultPackage = *publicationState.vaultPackage;
	*randomId = *publicationState.randomId;
	*yodaDOI = *publicationState.yodaDOI;
        *lastModifiedDateTime = *publicationState.lastModifiedDateTime;

	msiGetIcatTime(*now, "unix");
	*publicationDate = uuiso8601date(*now);
	*combiXmlPath = "*tempColl/*randomId-combi.xml";
	*systemMetadata =
	   "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" ++
	   "<metadata>\n" ++
	   "  <System>\n" ++
	   "    <Last_Modified_Date>*lastModifiedDateTime</Last_Modified_Date>\n" ++
	   "    <Persistent_Identifier_Datapackage>\n" ++
	   "       <Identifier_Scheme>DOI</Identifier_Scheme>\n" ++
	   "       <Identifier>*yodaDOI</Identifier>\n" ++
	   "    </Persistent_Identifier_Datapackage>\n" ++
	   "    <Publication_Date>*publicationDate</Publication_Date>\n" ++
	   "  </System>\n" ++
	   "</metadata>";

	msiDataObjOpen("objPath=*combiXmlPath++++openFlags=O_RDWRO_TRUNC", *fd);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);
	#DEBUG writeLine("serverLog", "iiGenerateSystemXml: generated *combiXmlPath");
	*publicationState.combiXmlPath = *combiXmlPath;
}

# \brief Determine the time of last modification as a datetime with UTC offset.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
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
	#DEBUG writeLine("serverLog", "iiGetLastModifiedDateTime: *lastModifiedDateTime");
}

# \brief Generate a Preliminary DOI. Preliminary, because we check for collision later.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGeneratePreliminaryDOI(*publicationConfig, *publicationState) {
	*dataCitePrefix = *publicationConfig.dataCitePrefix;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*length = int(*publicationConfig.randomIdLength);
	msiGenerateRandomID(*length, *randomId);
	*yodaDOI = "*dataCitePrefix/*yodaPrefix-*randomId";
	*publicationState.randomId = *randomId;
	*publicationState.yodaDOI = *yodaDOI;
	#DEBUG writeLine("serverLog", "iiGeneratePreliminaryDOI: *yodaDOI");
}


# \brief Upload dataCite XML to dataCite. This will register the DOI, without minting it.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiPostMetadataToDataCite(*publicationConfig, *publicationState){
	*dataCiteXmlPath = *publicationState.dataCiteXmlPath;
	*len = int(*publicationState.dataCiteXmlLen);
	msiDataObjOpen("objPath=*dataCiteXmlPath", *fd);
	msiDataObjRead(*fd, *len, *buf);
	msiDataObjClose(*fd, *status);
	msiBytesBufToStr(*buf, *dataCiteXml);
	msiRegisterDataCiteDOI(*dataCiteXml, *httpCode);
	if (*httpCode == "201") {
		*publicationState.dataCiteMetadataPosted = "yes";
		succeed;
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "500" || *httpCode == "503" || *httpCode == "504") {
	        # Unauthorized, Forbidden, Internal Server Error
		*publicationState.status = "Retry";
		writeLine("serverLog", "iiPostMetadataToDataCite: *httpCode received. Will be retried later.");
	} else {
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiPostMetadataToDataCite: *httpCode received. Unrecoverable error.");
	}
}

# \brief Remove metadata XML from DataCite.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiRemoveMetadataFromDataCite(*publicationConfig, *publicationState){
	*yodaDOI = *publicationState.yodaDOI;
	msiRemoveDataCiteMetadata(*yodaDOI, *httpCode);
	if (*httpCode == "200") {
		*publicationState.dataCiteMetadataPosted = "yes";
		succeed;
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "500" || *httpCode == "503" || *httpCode == "504") {
	        # Unauthorized, Forbidden, Internal Server Error
		*publicationState.status = "Retry";
		writeLine("serverLog", "iiRemoveMetadataFromDataCite: *httpCode received. Will be retried later");
	} else if (*httpCode == "404") {
		# Invalid DOI
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiRemoveMetadataFromDataCite: 404 Not Found - Invalid DOI");
	} else {
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiRemoveMetadataFromDataCite: *httpCode received. Unrecoverable error.");
	}
}

# \brief Announce the landing page URL for a DOI to dataCite. This will mint the DOI.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiMintDOI(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	*landingPageUrl = *publicationState.landingPageUrl;

	*request = "doi=*yodaDOI\nurl=*landingPageUrl\n";
	msiRegisterDataCiteDOI(*request, *httpCode);
	#DEBUG writeLine("serverLog", "iiMintDOI: *httpCode");
	if (*httpCode == "201") {
		*publicationState.DOIMinted = "yes";
		succeed;
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "412" || *httpCode == "500" || *httpCode == "503" || *httpCode == "504") {
                # Unauthorized, Forbidden, Precondition failed, Internal Server Error
		*publicationState.status = "Retry";
		writeLine("serverLog", "iiMintDOI: *httpCode received. Could be retried later");
		succeed;
	} else if (*httpCode == "400") {
                # Bad Request
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiMintDOI: 400 Bad Request - request body must be exactly two lines: DOI and URL; wrong domain, wrong prefix");
		succeed;
	} else {
		*publicationState.status = "Unrecoverable";
		writeLine("serverLog", "iiMintDOI: *httpCode received. Unrecoverable error.");
	}
}

# \brief Generate a URL for the landing page.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
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
	#DEBUG writeLine("serverLog", "iiGenerateLandingPageUrl: *landingPageUrl");
}

# \brief Generate a Landing page from the combi XML using XSLT.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGenerateLandingPage(*publicationConfig, *publicationState, *publish)
{
        *combiXmlPath = *publicationState.combiXmlPath;
        *randomId = *publicationState.randomId;
        uuChopPath(*combiXmlPath, *tempColl, *_);

        *vaultPackage = *publicationState.vaultPackage;
        *pathElems = split(*vaultPackage, "/");
        *rodsZone = elem(*pathElems, 0);
        *vaultGroup = elem(*pathElems, 2);

        uuGetBaseGroup(*vaultGroup, *baseGroup);
        uuGroupGetCategory(*baseGroup, *category, *subcategory);

	if (*publish == "publish") {
		*landingPageXslPath = "";
		*xslColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
		*xslName = IILANDINGPAGEXSLNAME;
		foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		        *landingPageXslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}

		if (*landingPageXslPath == "") {
		        *landingPageXslPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IILANDINGPAGEXSLNAME;
	        }
        } else {
                *landingPageXslPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIEMPTYLANDINGPAGEXSLNAME;
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
		#DEBUG writeLine("serverLog", "landing page len=*len");
		*publicationState.landingPageLen = str(*len);
		*publicationState.landingPagePath = *landingPagePath;
		#DEBUG writeLine("serverLog", "iiGenerateLandingPage: Generated *landingPagePath");
	}
}

# \brief iiCopyLandingPage2PublicHost
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
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
		#DEBUG writeLine("serverLog", "iiCopyLandingPage2PublicHost: pushed *publicPath");
	}
}

# \brief Use secure copy to push the combi XML to MOAI.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
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
		#DEBUG writeLine("serverLog", "iiCopyMetadataToMOAI: pushed *combiXmlPath");
	}

}

# \brief Set access restriction for vault package.
#
# \param[in] vaultPackage           Path to the package in the vault
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiSetAccessRestriction(*vaultPackage, *publicationState) {
        *accessRestriction = *publicationState.accessRestriction;

	*accessLevel = "null";
	if (*publicationState.accessRestriction like "Open*") {
	   *accessLevel = "read";
	}

	*err = errorcode(msiSetACL("recursive", *accessLevel, "anonymous", *vaultPackage));
	if (*err < 0) {
		writeLine("serverLog", "iiSetAccessRestriction: msiSetACL *accessLevel on *vaultPackage to anonymous returned errorcode *err");
		*publicationState.status = "Unrecoverable";
		succeed;
	}

	# We cannot set "null" as value in a kvp as this will crash msi_json_objops if we ever perform a uuKvp2JSON on it.
	if (*accessLevel == "null") {
		*publicationState.anonymousAccess = "no";
	} else {
		*publicationState.anonymousAccess = "yes";
	}
	#DEBUG writeLine("serverLog", "iiSetAccessRestriction: anonymous access level *accessLevel on *vaultPackage");
}

# \brief Configuration is extracted from metadata on the UUSYSTEMCOLLECTION.
#
# \param[out] publicationConfig  a key-value-pair containing the configuration
#
iiGetPublicationConfig(*publicationConfig) {
	# Translation from camelCase config key to snake_case metadata attribute
	*configKeys = list(
		 "publicHost",
		 "publicVHost",
		 "moaiHost",
		 "yodaPrefix",
		 "dataCitePrefix",
		 "randomIdLength",
		 "yodaInstance",
		 "davrodsVHost",
		 "davrodsAnonymousVHost"
		 );
	*metadataAttributes = list(
		 "public_host",
		 "public_vhost",
		 "moai_host",
		 "yoda_prefix",
		 "datacite_prefix",
		 "random_id_length",
		 "yoda_instance",
		 "davrods_vhost",
		 "davrods_anonymous_vhost");

	*nKeys = size(*configKeys);
	*sysColl = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;

	#DEBUG writeLine("serverLog", "iiGetPublicationConfig: fetching publication configuration from *sysColl");
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
	#DEBUG writeKeyValPairs("serverLog", *publicationConfig, "=");
}

# \brief The publication state is kept as metadata on the vaultPackage.
#
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
#
iiGetPublicationState(*vaultPackage, *publicationState) {
	# defaults
	msiString2KeyValPair("", *publicationState);
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

	*license = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME like '%License' AND COLL_NAME = *vaultPackage) {
		*license = *row.META_COLL_ATTR_VALUE;
	}


	if (*license != "") {

		*publicationState.license = *license;
		*licenseAttrName = UUORGMETADATAPREFIX ++ "license_uri";
		*licenseUri = "";
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *licenseAttrName AND COLL_NAME = *vaultPackage) {
			*licenseUri = *row.META_COLL_ATTR_VALUE;
		}

		if (*licenseUri != "") {
			*publicationState.licenseUri = *licenseUri;
		}
	}

	*publicationState.vaultPackage = *vaultPackage;
	#DEBUG writeKeyValPairs("serverLog", *publicationState, "=");
}

# \brief Save the publicationState key-value-pair to AVU's on the vaultPackage.
#
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
#
iiSavePublicationState(*vaultPackage, *publicationState) {
	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
                if (*val == "") {
                        *val = "REMOVE_KEY";
                }
		*attrName = UUORGMETADATAPREFIX ++ "publication_" ++ *key;
		*kvp."*attrName" = *val;
	}
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");

	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
                if (*val == "") {
                        *attrName = UUORGMETADATAPREFIX ++ "publication_" ++ *key;
                        *kvp."*attrName" = "REMOVE_KEY";
                }
	}
	msiRemoveKeyValuePairsFromObj(*kvp, *vaultPackage, "-C");
}

# \brief Request DOI to check on availibity. We want a 404 as return code.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pair
#
iiCheckDOIAvailability(*publicationConfig, *publicationState) {
	*yodaDOI = *publicationState.yodaDOI;
	msiGetDataCiteDOI(*yodaDOI, *result, *httpCode);
	if (*httpCode == "404") {
		# DOI is available!
		*publicationState.DOIAvailable = "yes";
		succeed;
	} else if (*httpCode == "401" || *httpCode == "403" || *httpCode == "500" || *httpCode == "503" || *httpCode == "504") {
		# request failed, worth a retry
		writeLine("serverLog", "iiCheckDOIAvailability: returned *httpCode; Could be retried later");
		*publicationState.status = "Retry";
	} else if (*httpCode == "200" || *httpCode == "204") {
		# DOI already in use.
		writeLine("serverLog", "DOI *yodaDOI already in use.\n*result");
		*publicationState.DOIAvailable = "no";
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

# \brief Routine to process a publication with sanity checks at every step.
#
# \param[in] vaultPackage       path to package in the vault to publish
# \param[out] status		status of the publication
#
iiProcessPublication(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != APPROVED_FOR_PUBLICATION &&
	    *vaultStatus != PUBLISHED) {
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
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGeneratePreliminaryDOI");
		iiGeneratePreliminaryDOI(*publicationConfig, *publicationState);
		iiSavePublicationState(*vaultPackage, *publicationState);
	} else if (iiHasKey(*publicationState, "DOIAvailable")) {
		if  (*publicationState.DOIAvailable == "no") {
			#DEBUG writeLine("serverLog", "iiProcessPublication: DOI not available, starting iiGeneratePreliminaryDOI");
			iiGeneratePreliminaryDOI(*publicationConfig, *publicationState);
			# We need to generate new XMLs
			*publicationState.combiXmlPath = "";
			*publicationState.dataCiteXmlPath = "";
			iiSavePublicationState(*vaultPackage, *publicationState);
		}
	}

	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);


	if (!iiHasKey(*publicationState, "combiXmlPath")) {
		# Generate Combi XML consisting of user and system metadata

		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateCombiXml");
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
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateDataCiteXml");
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
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCheckDOIAvailability");
		*err = errorcode(iiCheckDOIAvailability(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteMetadataPosted")) {
		# Send DataCite XML to metadata end point
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiPostMetadataToDataCite");
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
		*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"));
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPage");
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
	#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPageUrl");
	iiGenerateLandingPageUrl(*publicationConfig, *publicationState);

	if(!iiHasKey(*publicationState, "landingPageUploaded")) {
		# Use secure copy to push landing page to the public host
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCopyLandingPage2PublicHost");
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
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCopyMetadataToMOAI");
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

	if (!iiHasKey(*publicationState, "anonymousAccess")) {
		# Set access restriction for vault package.
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiSetAccessRestriction");
		*err = errorcode(iiSetAccessRestriction(*vaultPackage, *publicationState));
		if (*err < 0) {
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
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiMintDOI");
		*err = errorcode(iiMintDOI(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			iiSavePublicationState(*vaultPackage, *publicationState);
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

		        # Retrieve package title for notifications.
			*title = "";
			*titleKey = UUUSERMETADATAPREFIX ++ "0_Title";
			foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *titleKey) {
			        *title = *row.META_COLL_ATTR_VALUE;
			        break;
			}

		        # Send datamanager publication notification.
			*datamanager = "";
			*actorKey = UUORGMETADATAPREFIX ++ "publication_approval_actor";
			foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *actorKey) {
			        *userNameAndZone = *row.META_COLL_ATTR_VALUE;
				uuGetUserAndZone(*userNameAndZone, *datamanager, *zone);
			        break;
			}

			uuNewPackagePublishedMail(*datamanager, uuClientFullName, *title, *publicationState.yodaDOI, *mailStatus, *message);
			if (int(*mailStatus) != 0) {
			    writeLine("serverLog", "iiProcessPublication: Datamanager notification failed: *message");
			}

			# Send researcher publication notification.
			*researcher = "";
			*actorKey = UUORGMETADATAPREFIX ++ "publication_submission_actor";
			foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *actorKey) {
			        *userNameAndZone = *row.META_COLL_ATTR_VALUE;
				uuGetUserAndZone(*userNameAndZone, *researcher, *zone);
			        break;
			}

			uuYourPackagePublishedMail(*researcher, uuClientFullName, *title, *publicationState.yodaDOI, *mailStatus, *message);
			if (int(*mailStatus) != 0) {
			    writeLine("serverLog", "iiProcessPublication: Researcher notification failed: *message");
			}
		}
	} else {
	        writeLine("serverLog", "iiProcessPublication: All steps for publication completed");
	        # The publication was a success;
	        *publicationState.status = "OK";
	        iiSavePublicationState(*vaultPackage, *publicationState);
		*status = *publicationState.status;

		iiAddActionLogRecord("system", *vaultPackage, "publication updated");
	}
}


# \brief Process a depublication with sanity checks at every step.
#
# \param[in] vaultPackage       path to package in the vault to depublish
# \param[out] status		status of the depublication
#
iiProcessDepublication(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PENDING_DEPUBLICATION) {
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
	# Reset state on first call
	if (*publicationState.status == "OK") {
		iiSetUpdatePublicationState(*vaultPackage, *status);
		iiGetPublicationState(*vaultPackage, *publicationState);
		*publicationState.accessRestriction = "Closed";
	}
	*status = *publicationState.status;
	if (*status == "Unrecoverable" || *status == "Processing") {
		succeed;
	} else if (*status == "Unknown" || *status == "Retry") {
		*status = "Processing";
		*publicationState.status = "Processing";
	}


	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);

	if (!iiHasKey(*publicationState, "combiXmlPath")) {
		# Generate "Combi" XML consisting of only system metadata

		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiGenerateSystemXml");
		*err = errorcode(iiGenerateSystemXml(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteMetadataPosted")) {
		# Remove metadata from DataCite
		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiRemoveMetadataFromDataCite");
		*err = errorcode(iiRemoveMetadataFromDataCite(*publicationConfig, *publicationState));
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
		*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "depublish"));
		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiGenerateLandingPage");
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if(!iiHasKey(*publicationState, "landingPageUploaded")) {
		# Use secure copy to push landing page to the public host
		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiCopyLandingPage2PublicHost");
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
		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiCopyMetadataToMOAI");
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

	if (!iiHasKey(*publicationState, "anonymousAccess")) {
		# Set access restriction for vault package.
		#DEBUG writeLine("serverLog", "iiProcessDepublication: starting iiSetAccessRestriction");
		*err = errorcode(iiSetAccessRestriction(*vaultPackage, *publicationState));
		if (*err < 0) {
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_status=" ++ DEPUBLISHED, *vaultStatusKvp);
	msiSetKeyValuePairsToObj(*vaultStatusKvp, *vaultPackage, "-C");
	writeLine("serverLog", "iiProcessDepublication: All steps for depublication completed");
	# The depublication was a success;
	*publicationState.status = "OK";
	iiSavePublicationState(*vaultPackage, *publicationState);
	*status = *publicationState.status;
}


# \brief Routine to process a republication with sanity checks at every step.
#
# \param[in] vaultPackage       path to package in the vault to publish
# \param[out] status		status of the publication
#
iiProcessRepublication(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PENDING_REPUBLICATION) {
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
	# Reset state on first call
	if (*publicationState.status == "OK") {
		iiSetUpdatePublicationState(*vaultPackage, *status);
		iiGetPublicationState(*vaultPackage, *publicationState);
	}
	*status = *publicationState.status;
	if (*status == "Unrecoverable" || *status == "Processing") {
		succeed;
	} else if (*status == "Unknown" || *status == "Retry") {
		*status = "Processing";
		*publicationState.status = "Processing";
	}


	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);

	if (!iiHasKey(*publicationState, "combiXmlPath")) {
		# Generate Combi XML consisting of user and system metadata

		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiGenerateCombiXml");
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
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiGenerateDataCiteXml");
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteMetadataPosted")) {
		# Send DataCite XML to metadata end point
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiPostMetadataToDataCite");
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
		*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"));
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiGenerateLandingPage");
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if(!iiHasKey(*publicationState, "landingPageUploaded")) {
		# Use secure copy to push landing page to the public host
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiCopyLandingPage2PublicHost");
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
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiCopyMetadataToMOAI");
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

	if (!iiHasKey(*publicationState, "anonymousAccess")) {
		# Set access restriction for vault package.
		#DEBUG writeLine("serverLog", "iiProcessRepublication: starting iiSetAccessRestriction");
		*err = errorcode(iiSetAccessRestriction(*vaultPackage, *publicationState));
		if (*err < 0) {
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_status=" ++ PUBLISHED, *vaultStatusKvp);
	msiSetKeyValuePairsToObj(*vaultStatusKvp, *vaultPackage, "-C");
	writeLine("serverLog", "iiProcessRepublication: All steps for republication completed");
	# The depublication was a success;
	*publicationState.status = "OK";
	iiSavePublicationState(*vaultPackage, *publicationState);
	*status = *publicationState.status;
}

# \brief Routine to set publication state of vault package pending to update.
#
# \param[in]  vaultPackage   path to package in the vault to update
# \param[out] status         status of the publication state update
#
iiSetUpdatePublicationState(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PUBLISHED &&
	    *vaultStatus != PENDING_DEPUBLICATION &&
	    *vaultStatus != PENDING_REPUBLICATION) {
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
		*status = "UnkownError";
		succeed;
	}

	# Load state
	iiGetPublicationState(*vaultPackage, *publicationState);
	if (*publicationState.status != "OK") {
		*status = "PublicationNotOK";
		succeed;
	}

	# Set publication status
	*publicationState.status = "Unknown";

	# Generate new XML's
	*publicationState.combiXmlPath = "";
	*publicationState.dataCiteXmlPath = "";

	# Post metadata to DataCite
	*publicationState.dataCiteMetadataPosted = "";

	# Generate new landingpage
	*publicationState.landingPagePath = "";
	*publicationState.landingPageUploaded = "";

	# Update OAI-PMH metadata
	*publicationState.oaiUploaded = "";

	# Update anonymous access
	*publicationState.anonymousAccess = "";

	# Save state
	*err = errorcode(iiSavePublicationState(*vaultPackage, *publicationState));
	if (*err < 0) {
		*status = "UnkownError";
		succeed;
	}
}


# \brief Routine to update the landingpage of a published package.
#
# \param[in]  vaultPackage      path to package in the vault to publish
# \param[out] status		status of the publication
#
iiUpdateLandingpage(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PUBLISHED && *vaultStatus != DEPUBLISHED) {
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

	# Publication must be finsished.
	if (*publicationState.status != "OK") {
		*status = "NotAllowed";
		succeed;
	}

	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);

	# Create landing page
	#DEBUG writeLine("serverLog", "iiUpdateLandingpage: starting iiGenerateLandingPage");
	*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"));
	if (*err < 0) {
		*status = "Unrecoverable";
		succeed;
	}

	# Use secure copy to push landing page to the public host
	#DEBUG writeLine("serverLog", "iiUpdateLandingpage: starting iiCopyLandingPage2PublicHost");
	*err = errorcode(iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState));
	if (*err < 0) {
		*status = "Retry";
		succeed;
	}

	# The update was a success;
	writeLine("serverLog", "iiUpdateLandingpage: landingpage updated for *vaultPackage");	
	*status = "OK";
}