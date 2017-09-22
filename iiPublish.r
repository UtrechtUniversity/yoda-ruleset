# \file iiPublish.r
# \brief This file contains rules related to publishing a datapackage
# 		for a research group
#
# \author Paul Frederiks
#
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiGenerateDataciteXml
iiGenerateDataCiteXml(*combiXmlPath, *dataCiteXml) {
	*pathElems = split(*combiXmlPath, "/");
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
		*dataCiteXml = "";
	} else {
 		msiBytesBufToStr(*buf, *dataCiteXml);
	}
}

# \brief iiGenerateCombiXml
iiGenerateCombiXml(*vaultPackage, *combiXmlPath){

	iiGetDOIFromMetadata(*vaultPackage, *yodaDOI);
	
	iiGetLastModifiedDate(*vaultPackage, *lastModifiedDate);
	*subPath = triml(*vaultPackage, "/home/");
	msiGetIcatTime(*now, "unix");
	*publicationDate = uuiso8601date(*now);

	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*combiXmlPath = "*vaultPackage/*baseName-publication[*publicationDate].*extension";

	*systemMetadata =
	   "  <system>\n" ++
	   "    <Last_Modified_Date>*lastModifiedDate</Last_Modified_Date>\n" ++
	   "    <Persistent_Identifier_Datapackage>*yodaDOI</Persistent_Identifier_Datapackage>\n" ++
	   "    <Persistent_Identifier_Datapackage_Type>DOI</Persistent_Identifier_Datapackage_Type>\n" ++
           "    <Publication_Date>*publicationDate</Publication_Date>\n" ++
           "    <Open_Access_Link><![CDATA[http://public.yoda.uu.nl/*subPath]]></Open_Access_Link>\n" ++
           "  </system>\n" ++ 
           "</metadata>";

	iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath);

	msiDataObjCopy(*metadataXmlPath, *combiXmlPath, "forceFlag=", *status);
	msiDataObjOpen("objPath=*combiXmlPath++++openFlags=O_RDWR", *fd);
	msiDataObjLseek(*fd, -12, "SEEK_END", *status);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);

	iiCopyACLsFromParent(*combiXmlPath);
}

# \brief iiGetLastModifiedDate
iiGetLastModifiedDate(*vaultPackage, *lastModifiedDate) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";
	foreach(*row in SELECT order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE
                                          WHERE META_COLL_ATTR_NAME = *actionLog
                                          AND COLL_NAME = *vaultPackage) {
		*logRecord = *row.META_COLL_ATTR_VALUE;
		break;
	}

	*lastModifiedTimestamp = "";
	msi_json_arrayops(*logRecord, *lastModifiedTimestamp, "get", 0);
	*lastModifiedDate = uuiso8601date(*lastModifiedTimestamp);
}



# \brief iiGeneratePreliminaryDOI
iiGeneratePreliminaryDOI(*vaultPackage, *yodaDOI) {
	*dataCitePrefix = UUDOIPREFIX;
	*yodaPrefix = UUDOIYODAPREFIX;
	msiGenerateRandomID(UURANDOMIDLENGTH, *randomID);
	*yodaDOI = "*dataCitePrefix/*yodaPrefix-*randomID";
	msiString2KeyValPair(UUORGMETADATAPREFIX++"DOI="++*yodaDOI, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

# \brief iiGetDOIFromMetadata
iiGetDOIFromMetadata(*vaultPackage, *yodaDOI) {
	*doiAttrName = UUORGMETADATAPREFIX ++ "DOI";
	*yodaDOI = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE
			WHERE META_COLL_ATTR_NAME = *doiAttrName
			AND COLL_NAME = *vaultPackage) {	
		*yodaDOI = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief iiPostMetadataToDataCite
iiPostMetadataToDataCite(*dataCiteXml){ 
	*dataCiteUrl = UUDATACITESERVER ++ "/metadata";
	iiGetDataCiteCredentials(*username, *password);
	msiRegisterDataCiteDOI(*dataCiteUrl, *username, *password, *dataCiteXml, *httpCode);
	writeLine("serverLog", "iiPostMetadataToDataCite: HTTP CODE *httpCode");
}

# \brief iiMintDOI
iiMintDOI(*yodaDOI, *landingPage) {
	*dataCiteUrl = UUDATACITESERVER ++ "/doi";
	iiGetDataCiteCredentials(*username, *password);

	*request = "doi=*yodaDOI\nurl=*landingPage\n";
	msiRegisterDataCiteDOI(*dataCiteUrl, *username, *password, *request, *httpCode); 
	writeLine("serverLog", "iiMintDOI: HTTP CODE *httpCode");
}


# \brief iiGetDataCiteCredentials
iiGetDataCiteCredentials(*username, *password) {
	*username = "";
	*password = "";
	*sysColl = "/"++$rodsZoneClient++UUSYSTEMCOLLECTION;

	*prefix = UUORGMETADATAPREFIX++"datacite_";
	iiCollectionMetadataKvpList(*sysColl, *prefix, true, *lst);
	foreach(*kvp in *lst) {
		if (*kvp.attrName == "username") {
			*username = *kvp.attrValue;
		} else if (*kvp.attrName == "password") {
			*password = *kvp.attrValue;
		}
	}

	if (*username == "" || *password == "") {
		writeLine("serverLog", "iiGetDataCiteCredentials: No credentials found");
		fail;
	}
}

iiGenerateLandingPageUrl(*vaultPackage, *yodaDOI, *landingPageUrl) {
	*instance = UUINSTANCENAME;
	*yodaPrefix = UUDOIYODAPREFIX;
	*randomId = triml(*yodaDOI, "-");
	*landingPageUrl = "https://public.yoda.uu.nl/*instance/*yodaPrefix/*randomId";	
	msiString2KeyValPair(UUORGMETADATAPREFIX++"landing_page_url="++*landingPageUrl, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

iiGetLandingPageUrlFromMetadata(*vaultPackage, *landingPage) {
	*landingPage = "";
	*attrName = UUORGMETADATAPREFIX++"landing_page_url";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *attrName) {
		*landingPage = *row.META_COLL_ATTR_VALUE;
	}
}

iiGenerateLandingPage(*combiXmlPath, *landingPagePath) {
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
		*landingPagePath = "";
	} else {
		msiGetIcatTime(*now, "unix");
		*publicationDate = uuiso8601date(*now);
		uuChopPath(*combiXmlPath, *vaultPackage, *_);
		*landingPagePath = "*vaultPackage/landingpage[*publicationDate].html";
 		msiDataObjCreate(*landingPagePath, "forceFlag=", *fd);
		msiDataObjWrite(*fd, *buf, *len);
		msiDataObjClose(*fd, *status);
		
		iiCopyACLsFromParent(*landingPagePath);
	}
}

iiProcessPublication(*vaultPackage, *status) {
	*status = "FAILED";

	writeLine("serverLog", "iiProcessPublication: processing *vaultPackage");
	iiGetDOIFromMetadata(*vaultPackage, *yodaDOI);
	writeLine("serverLog", "iiProcessPublication: DOI in metadata is *yodaDOI");
	if (*yodaDOI == "") {
		iiGeneratePreliminaryDOI(*vaultPackage, *yodaDOI);
		writeLine("serverLog", "iiProcessPublication: Generated DOI is *yodaDOI");
	}

	iiGenerateCombiXml(*vaultPackage, *combiXmlPath) ::: succeed;
	writeLine("serverLog", "iiProcessPublication: combiXmlPath is *combiXmlPath");

	iiGenerateDataCiteXml(*combiXmlPath, *dataCiteXml) ::: succeed;
	writeLine("serverLog", "iiProcessPublication: dataCiteXml\n*dataCiteXml");
	if (*dataCiteXml == "") {
		fail;
	}

	iiPostMetadataToDataCite(*dataCiteXml) ::: succeed;
		
	iiGetLandingPageUrlFromMetadata(*vaultPackage, *landingPageUrl) ::: succeed;
	writeLine("serverLog", "iiGetLandingPageUrlFromMetadata: *landingPageUrl");
	if (*landingPageUrl == "") {	
		iiGenerateLandingPage(*combiXmlPath, *landingPagePath) ::: succeed;
		writeLine("serverLog", "iiProcessPublication: landingPagePath *landingPagePath");

		iiGenerateLandingPageUrl(*vaultPackage, *yodaDOI, *landingPageUrl) ::: succeed;
		writeLine("serverLog", "iiGenerateLandingPageUrl: *landingPageUrl");
	}
	
	iiMintDOI(*yodaDOI, *landingPageUrl) ::: succeed;
	*status = "OK";

}
