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
		*dataCiteXslPath = "/" ++ *rodsZone ++ IIXSLCOLLECTION ++ "/" ++ IIDATACITEDEFAULTNAME;
	}
	msiXsltApply(*dataCiteXslPath, *combiXmlPath, *buf);
 	msiBytesBufToStr(*buf, *dataCiteXml);
}

# \brief iiGenerateCombiXml
iiGenerateCombiXml(*vaultPackage, *combiXmlPath){

	iiGetDOIFromMetadata(*vaultPackage, *yodaDOI);
	
	iiGetLastModifiedDate(*vaultPackage, *lastModifiedDate);	

	msiGetIcatTime(*now, "unix");
	*publicationDate = uuiso8601date(*now);

	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*combiXmlPath = "*vaultPackage/*baseName-publication[*publicationDate].*extension";

	*systemMetadata =
	   "  <system>\n" ++
	   "    <Persistent_Identifier_Datapackage>*yodaDOI</Persistent_Identifier_Datapackage>\n" ++
	   "    <Persistent_Identifier_Datapackage_Type>DOI</Persistent_Identifier_Datapackage_Type>\n" ++
	   "    <Last_Modified_Date>*lastModifiedDate</Last_Modified_Date>\n" ++
           "    <Publication_Date>*publicationDate</Publication_Date>\n" ++
           "  </system>\n" ++ 
           "</metadata>";

	iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath);

	msiDataObjCopy(*metadataXmlPath, *combiXmlPath, "forceFlag=", *status);
	msiDataObjOpen("objPath=*combiXmlPath++++openFlags=O_RDWR", *fd);
	msiDataObjLseek(*fd, -12, "SEEK_END", *status);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);
}

# \brief iiGetLastModifiedDate
iiGetLastModifiedDate(*vaultPackage, *lastModifiedDate) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";
	foreach(*row in SELECT order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *actionLog and COLL_NAME = *vaultPackage) {
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
}

# \brief iiMintDOI
iiMintDOI(*yodaDOI, *landingPage) {
	*dataCiteUrl = UUDATACITESERVER ++ "/doi";
	iiGetDataCiteCredentials(*username, *password);

	*request = "doi=*yodaDOI\nurl=*landingPage\n";
	msiRegisterDataCiteDOI(*dataCiteUrl, *username, *password, *request, *httpCode); 
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
	msiString2KeyValPair(UUORGMETADATAPREFIX++"landing_page="++*landingPageUrl, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

iiGetLandingPageFromMetadata(*vaultPackage, *landingPage) {
	*landingPage = "";
	*attrName = UUORGMETADATAPREFIX++"landing_page";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *attrName) {
		*landingPage = *row.META_COLL_ATTR_VALUE;
	}
}

iiProcessPublication(*vaultPackage) {
	iiGetDOIFromMetadata(*vaultPackage, *yodaDOI);
	if (*yodaDOI == "") {
		iiGeneratePreliminaryDOI(*vaultPackage, *yodaDOI);
	}

	iiGenerateCombiXml(*vaultPackage, *combiXmlPath);

	iiGenerateDataCiteXml(*combiXmlPath, *dataCiteXml);

	iiPostMetadataToDataCite(*dataCiteXml);
	
	iiGetLandingPageUrlFromMetadata(*vaultPackage, *landingPageUrl);
	if (*landingPageUrl == "") {	
		iiGenerateLandingPageUrl(*vaultPackage, *yodaDOI, *landingPageUrl);
	}
	
	iiMintDOI(*yodaDOI, *landingPageUrl);
}
