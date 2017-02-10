# \file
# \brief This file contains rules related to metadata
#                       to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief GetAvailableValuesForKeyLike Returns list of values that exist in the
# 										icat database for a certain key, which
# 										are like a certain value
#
# \param[in] *key 						Key to look for
# \param[in] *searchString 				String that should be a substring of the
# 										returned values
# \param[in] *isCollection 				Wether to look in collection or data 
# \param[out] *values 					List of possible values for the given key
# 										where the given search string is a substring of
uuIiGetAvailableValuesForKeyLike(*key, *searchString, *isCollection, *values){
	*values = list();

	if(*isCollection){
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE 
			META_COLL_ATTR_NAME like '*key' AND
			META_COLL_ATTR_VALUE like '%*searchString%') {
			writeLine("stdout", *row.META_COLL_ATTR_VALUE);
			*values = cons(*row.META_COLL_ATTR_VALUE,*values);
			writeLine("serverLog", *row.META_COLL_ATTR_VALUE);
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE 
			META_DATA_ATTR_NAME like '*key' AND
			META_DATA_ATTR_VALUE like '%*searchString%') {
			*values = cons(*row.META_DATA_ATTR_VALUE,*values);
		}
	}
}

# /brief iiPrepareMetadataImport	Locate the XSD to use for a metadata path. Use this rule when $rodsZoneClient is unavailable
# /param[in] metadataxmlpath		path of the metadata XML file that needs to be validated
# /param[in] rodsZone			irods zone to use
# /param[out] xsdpath			path of the XSD to use for validation
# /param[out] xslpath			path of the XSL to use for conversion to an AVU xml
iiPrepareMetadataImport(*metadataxmlpath, *rodsZone, *xsdpath, *xslpath) {
	*xsdpath = "";
	*xslpath = "";
	*isfound = false;
	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	foreach(*row in
	       	SELECT USER_GROUP_NAME
	       	WHERE COLL_NAME = *metadataxml_coll
	          AND DATA_NAME = *metadataxml_basename
	          AND USER_GROUP_NAME like "research-%"
		  ) {
		if(!*isfound) {
			*groupName = *row.USER_GROUP_NAME;
			*isfound = true;
	 	} else {
			# Too many query results. More than one group associated with file.
			fail(-54000);
		}
	}

	if (!*isfound) {
		# No results found. Not a research group
		fail(-808000);
	}

	uuGroupGetCategory(*groupName, *category, *subcategory);
	*xsdcoll = "/*rodsZone" ++ IIXSDCOLLECTION;
	*xsdname = "*category.xsd";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdcoll AND DATA_NAME = *xsdname) {
		*xsdpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*xsdpath == "") {
		*xsdpath = "/*rodsZone" ++ IIXSDCOLLECTION ++ "/" ++ IIXSDDEFAULTNAME;
	}
	
	*xslcoll = "/*rodsZone" ++ IIXSDCOLLECTION;
	*xslname = "*category.xsl";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslcoll AND DATA_NAME = *xslname) {
		*xslpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*xslpath == "") {
		*xslpath = "/*rodsZone" ++ IIXSLCOLLECTION ++ "/" ++ IIXSLDEFAULTNAME;
	}
}

# /brief iiPrepareMetadataForm	return info needed for the metadata form
# /param[in] path	path of the collection where metadata needs to be viewed or added
# /param[out] result	json object with the location of the metadata file, formelements.xml, the XSD and the role of the current user in the group
iiPrepareMetadataForm(*path, *result) {
	msiString2KeyValPair("", *kvp);

	*isfound = false;
	*prefix = IIGROUPPREFIX ++ "%";
	foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
		*id = *accessid.COLL_ACCESS_USER_ID;
		foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id AND USER_GROUP_NAME like *prefix) {
				*isfound = true;
				*groupName = *group.USER_GROUP_NAME;
		}
	}


	if (!*isfound) {
		# No results found. Not a research group
		failmsg(-808000, "path is not a research group or not available to current user");
	}
	
	uuGroupGetMemberType(*groupName, "$userNameClient#$rodsZoneClient", *usertype);
	*kvp.groupName = *groupName;
	*kvp.userType = *usertype;

	*xmlname = IIMETADATAXMLNAME;	
	*xmlpath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *path AND DATA_NAME = *xmlname) {
	        *xmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*xmlpath == "") {
		*kvp.hasMetadataXml = "false";
		*kvp.metadataXmlPath = *path ++ "/" ++ IIMETADATAXMLNAME;
		uuChopPath(*path, *parent, *child);
		foreach(*row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *parent AND DATA_NAME = *xmlname) {
			*kvp.parentMetadataXml = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}
	} else {
		*kvp.hasMetadataXml = "true";
		*kvp.metadataXmlPath = *xmlpath;
	}	

	uuGroupGetCategory(*groupName, *category, *subcategory);
	*kvp.category = *category;
	*kvp.subcategory = *subcategory;
	*xsdcoll = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION;
	*xsdname = "*category.xsd";
	*xsdpath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdcoll AND DATA_NAME = *xsdname) {
		*xsdpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	
	if (*xsdpath == "") {
		*kvp.xsdPath = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/" ++ IIXSDDEFAULTNAME;
	} else {
		*kvp.xsdPath = *xsdpath;
	}

	*formelementscoll = "/" ++ $rodsZoneClient ++ IIFORMELEMENTSCOLLECTION;
	*formelementsname = "*category.xml";
	*formelementspath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *formelementscoll AND DATA_NAME = *formelementsname) {
		*formelementspath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*formelementspath == "") {
		*kvp.formelementsPath = "/" ++ $rodsZoneClient ++ IIFORMELEMENTSCOLLECTION ++ "/" ++ IIFORMELEMENTSDEFAULTNAME;
	} else {
		*kvp.formelementsPath = *formelementspath;
	}

	uuKvp2JSON(*kvp, *result);
}

# /brief iiAllRemoveMetadata	Remove the yoda-metadata.xml file and remove all user metadata from irods	
# /param[in] path		Path of collection to scrub of metadata
iiRemoveAllMetadata(*path) {
	*metadataxmlpath =  *path ++ "/" ++ IIMETADATAXMLNAME;
	msiAddKeyValToMspStr("objPath", *metadataxmlpath, *options);
	msiAddKeyValToMspStr("forceFlag", "", *options);
	*err = errorcode(msiDataObjUnlink(*options, *status));
	writeLine("serverLog", "iiRemoveMetadata *path returned errorcode: *err");
}

# /brief iiRemoveUserAVUs   Remove the User AVU's from the irods AVU store
# /param[in] coll	    Collection to scrub of user metadata
iiRemoveUserAVUs(*coll) {
	*prefix = UUUSERMETADATAPREFIX ++ "%";
	msiString2KeyValPair("", *kvp);

	*duplicates = list();
	*attrs = list();

	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		uuListContains(*attrs, *attr, *inList);
		if (*inList) {
			*duplicates = cons((*attr, *val), *duplicates);
		} else {
			*attrs = cons(*attr, *attrs);
			msiAddKeyVal(*kvp, *attr, *val);
			writeLine("serverLog", "iiRemoveUserAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		}
	}

	msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	
	foreach(*pair in *duplicates) {

		(*attr, *val) = *pair;
		writeLine("serverLog", "iiRemoveUserAVUs: Duplicate key Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *attr, *val);
		msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	}
}

# /brief iiImportMetadataFromXML Ingest user metadata from XML preprocessed with an XSLT
# /param[in] metadataxmlpath	path of metadataxml to ingest
# /param[in] xslpath		path of XSL stylesheet
iiImportMetadataFromXML (*metadataxmlpath, *xslpath) {

	# apply xsl stylesheet to metadataxml
	msiXsltApply(*xslpath, *metadataxmlpath, *buf);
	writeBytesBuf("serverLog", *buf);

	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	msiLoadMetadataFromXmlBuf(*metadataxml_coll, *buf);
}

# \brief iiCloneMetadataXml   Clone metadata file from one place to the other
# \param[in] *src	path of source metadataxml
# \param[in] *dst	path of destination metadataxml
iiCloneMetadataXml(*src, *dst) {
	msiDataObjCopy(*src, *dst, "", *status);
}


