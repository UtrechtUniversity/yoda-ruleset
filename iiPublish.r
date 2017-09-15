# \file iiPublish.r
# \brief This file contains rules related to publishing a datapackage
# 		for a research group
#
# \author Paul Frederiks
#
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiGenerateDataciteXml
iiGenerateDataciteXml(*metadataXmlPath, *dataCiteXml) {
	*pathElems = split(*metadataXmlPath, "/");
	*rodsZone = elem(*pathElems, 0);
	*vaultGroup = elem(*pathElems, 2);
	uuGetBaseGroup(*vaultGroup, *baseGroup);
	uuGroupGetCategory(*baseGroup, *category, *subcategory);

	*dataCiteXslPath = "";
	*xslColl = "/"++*rodsZone++IIXSLCOLLECTION;
	*xslName = "/"++*category++"2datacite.xml";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		*dataCiteXslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*dataCiteXslPath == "") {
		*dataCiteXslPath = "/" ++ *rodsZone ++ IIXSLCOLLECTION ++ "/" ++ IIDATACITEDEFAULTNAME;
	}

	uuChopPath(*metadataXmlPath, *vaultPackage, *metadataXmlName);
	*attrNameDOI = IIORGMETADATAPREFIX++"DOI";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *attrNameDOI) {
		*yodaDOI = *row.META_COLL_ATTR_VALUE;
	}	
	
	iiActionLog(*vaultPackage, *size, *actionLog);
	msi_json_arrayops(*actionLog, *lastLogItem, "get", *size-1);
	msi_json_arrayops(*lastLogItem, *lastModifiedTimestamp, "get", 0);
	*lastModifiedDate = uuiso8601date(*lastModifiedTimestamp);
	msiGetIcatTime(*now, "unix");
	*publicationDate = uuiso8601date(*now);

	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*combiXmlPath = "*vaultPackage/*baseName-publish[*publicationDate].*extension";

	*systemMetadata =
	   "<system>" ++
	   "  <Last_Modified_Date>*lastModifiedDate</Last_Modified_Date>\n" ++
	   "  <Persistent_Identifier_Datapackage>*yodaDOI</Persistent_Identifier_Datapackage>\n" ++
	   "  <Persistent_Identifier_Datapackage_Type>DOI</Persistent_Identifier_Datapackage_Type>\n" ++
	  "  <Publication_Date>*publicationDate</Publication_Date>\n" ++
	  "</system>\n</metadata>";

	msiDataObjCopy(*metadataXmlPath, *combiXmlPath, "forceFlag=", *status);
	msiDataObjOpen("objPath=*combiXmlPath++++openFlags=O_RDWR", *fd);
	msiDataObjLseek(*fd, -12, "SEEK_END", *status);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);

	msiXsltApply(*dataciteXslPath, *combiXmlPath, *buf);
 	msiBytesBufToStr(*buf, *dataCiteXml);
}


# \brief iiGeneratePreliminaryDOI
iiGeneratePreliminaryDOI(*vaultPackage, *yodaDOI) {
	*dataCitePrefix = UUDOIPREFIX;
	*yodaPrefix = UUDOIYODAPREFIX;
	msiGenerateRandomID(UURANDOMIDLENGTH, *randomID);
	*yodaDoi = "*dataCitePrefix/*yodaPrefix-*randomID";
	msiString2KeyValPair(UUORGMETADATAPREFIX++"DOI", *kvp);
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");
}

# \brief iiPostMetadataToDataCite
iiPostMetadataToDataCite(*dataciteXml){ 
	*dataCiteUrl = UUDATACITESERVER ++ "/metadata";
	iiGetDataCiteCredentials(*username, *password);
	msiRegisterDataCiteDOI(*dataciteUrl, *username, *password, *dataciteXml, *httpCode);
}

iiGetDataCiteCredentials(*username, *password) {
	*username = "";
	*password = "";
	*sysColl = "/"++$rodsZoneClient++UUSYSTEMCOLLECTION;

	*prefix = UUORGMETADATAPREFIX++"datacite";
	iiCollectionMetadataKvpList(*sysColl, *prefix, true, *lst);
	foreach(*kvp in *lst) {
		if (*kvp.attrName == "username") {
			*username = *kvp.attrValue;
		} else if (*kvp.attrName = "password") {
			*password = *kvp.attrValue;
		}
	}

	if (*username == "" || *password == "") {
		writeLine("serverLog", "iiGetDataCiteCredentials: No credentials found");
		fail;
	}
}
