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
iiGetAvailableValuesForKeyLike(*key, *searchString, *isCollection, *values){
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
	       	SELECT USER_NAME
	       	WHERE COLL_NAME = *metadataxml_coll
	          AND DATA_NAME = *metadataxml_basename
	          AND USER_NAME like "research-%"
		  ) {
		if(!*isfound) {
			*groupName = *row.USER_NAME;
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
	

	if (*path like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager); 
		*kvp.groupName = *groupName;
		*kvp.userType = *userType;
		if (*isDatamanager) {
			*kvp.isDatamanager = "yes";
		} else {
			*kvp.isDatamanager = "no";
		}

	} else {
		*result = "";
		succeed;	
	}

	iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, false, *kvpList);

	*orgStatus = FOLDER;
	foreach(*metadataKvp in *kvpList) {
		if (*metadataKvp.attrName == IISTATUSATTRNAME) {
			*orgStatus = *metadataKvp.attrValue;
			break;
		}
	}
	*kvp.folderStatus = *orgStatus;

	*lockFound = "no";
	foreach(*metadataKvp in *kvpList) {
		if (*metadataKvp.attrName == IILOCKATTRNAME) {
			*rootCollection = *metadataKvp.attrValue;
			if (*rootCollection == *path) {
				*lockFound = "here";
				break;
			} else {
				*descendants = triml(*rootCollection, *path);
				if (*descendants == *rootCollection) {
					*ancestors = triml(*path, *rootCollection);
					if (*ancestors == *path) {
						*lockFound = "outoftree";
					} else {
						*lockFound = "ancestor";
						break;
					}
				} else {
					*lockFound = "descendant";
					break;
				}
			}
		}
	}
	*kvp.lockFound = *lockFound;
	if (*lockFound != "no") {
		*kvp.lockRootCollection = *rootCollection;
	}

		
	
	*xmlname = IIMETADATAXMLNAME;	
	*xmlpath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *path AND DATA_NAME = *xmlname) {
	        *xmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*xmlpath == "") {
		*kvp.hasMetadataXml = "false";
		*kvp.metadataXmlPath = *path ++ "/" ++ IIMETADATAXMLNAME;
	} else {
		*kvp.hasMetadataXml = "true";
		*kvp.metadataXmlPath = *xmlpath;
		# check for locks on metadataXml
		iiDataObjectMetadataKvpList(*path, IILOCKATTRNAME, true, *metadataXmlLocks);
		uuKvpList2JSON(*metadataXmlLocks, *json_str, *size);
		*kvp.metadataXmlLocks = *json_str;	
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
		*xsdpath = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/" ++ IIXSDDEFAULTNAME;
	}
	*kvp.xsdPath = *xsdpath;

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

	uuChopPath(*path, *parent, *child);
	*kvp.parentHasMetadataXml = "false";
	foreach(*row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *parent AND DATA_NAME = *xmlname) {
		*parentxmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		*err = errormsg(msiXmlDocSchemaValidate(*parentxmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
		} else if (*err == 0) {
				*kvp.parentHasMetadataXml = "true";
				*kvp.parentMetadataXmlPath = *parentxmlpath;
		} else {
			writeLine("serverLog", "iiPrepareMetadataForm: *err");
			writeBytesBuf("serverLog", *status_buf);
		}
	}
	uuKvp2JSON(*kvp, *result);
}

# /brief iiRemoveAllMetadata	Remove the yoda-metadata.xml file and remove all user metadata from irods	
# /param[in] path		Path of collection to scrub of metadata
iiRemoveAllMetadata(*path) {
	*metadataxmlpath =  *path ++ "/" ++ IIMETADATAXMLNAME;
	msiAddKeyValToMspStr("objPath", *metadataxmlpath, *options);
	msiAddKeyValToMspStr("forceFlag", "", *options);
	*err = errorcode(msiDataObjUnlink(*options, *status));
	writeLine("serverLog", "iiRemoveMetadata *path returned errorcode: *err");
}

# \brief iiRemoveAVUs   Remove the User AVU's from the irods AVU store
# \param[in] coll	    Collection to scrub of user metadata
# \param[in] prefix	    prefix of metadata to remov
iiRemoveAVUs(*coll, *prefix) {
	writeLine("serverLog", "iiRemoveAVUs: Remove all AVU's from *coll prefixed with *prefix");
	msiString2KeyValPair("", *kvp);
	*prefix = *prefix ++ "%";

	*duplicates = list();
	*prev = "";
	foreach(*row in SELECT order_asc(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		if (*attr == *prev) {
			writeLine("serverLog", "iiRemoveAVUs: Duplicate attribute " ++ *attr);
		       *duplicates = cons((*attr, *val), *duplicates);
		} else {	
			msiAddKeyVal(*kvp, *attr, *val);
			writeLine("serverLog", "iiRemoveAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
			*prev = *attr;
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
	*err = errormsg(msiLoadMetadataFromXmlBuf(*metadataxml_coll, *buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiImportMetadataFromXML: *err - *msg ");
	} else {
		writeLine("serverLog", "iiImportMetadataFromXML: Succesfully loaded metadata from XML");
	}
}

# \brief iiCloneMetadataXml   Clone metadata file from one place to the other
# \param[in] *src	path of source metadataxml
# \param[in] *dst	path of destination metadataxml
iiCloneMetadataXml(*src, *dst) {
	writeLine("serverLog", "iiCloneMetadataXml:*src -> *dst");
	*err = errormsg(msiDataObjCopy(*src, *dst, "", *status), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiCloneMetadataXml: *err - *msg)");
	}
}

# \brief iiMetadataXmlModifiedPost
iiMetadataXmlModifiedPost(*xmlpath, *zone) {
	uuChopPath(*xmlpath, *parent, *basename);
	writeLine("serverLog", "iiMetadataXmlModifiedPost: *basename added to *parent. Import of metadata started");
	iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath);
	*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", *msg);
	} else if (*err == 0) {
		writeLine("serverLog", "XSD validation successful. Start indexing");
		iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
		iiImportMetadataFromXML(*xmlpath, *xslpath);
	} else {
		writeBytesBuf("serverLog", *status_buf);
	}
}

iiLogicalPathFromPhysicalPath(*physicalPath, *logicalPath, *zone) {
	*lst = split(*physicalPath, "/");
	# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
	uuListIndexOf(*lst, "home", *idx);
	if (*idx < 0) {
		writeLine("serverLog","iiLogicalPathFromPhysicalPath: Could not find home in *physicalPath. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		fail;
	}
	# skip to the part of the path starting from ../home/..
	for( *el = 0; *el < *idx; *el = *el + 1) {
		*lst = tl(*lst);
	}
	# Prepend with the zone and rejoin to a logical path
	*lst	= cons(*zone, *lst);
	uuJoin("/", *lst, *logicalPath);
	*logicalPath = "/" ++ *logicalPath;
	writeLine("serverLog", "iiLogicalPathFromPhysicalPath: *physicalPath => *logicalPath");
}


# \brief iiMetadataXmlRenamedPost
iiMetadataXmlRenamedPost(*src, *dst, *zone) {
	uuChopPath(*src, *src_parent, *src_basename);
	# the logical_path in $KVPairs is that of the destination
	uuChopPath(*dst, *dst_parent, *dst_basename);
	if (*dst_basename != IIMETADATAXMLNAME && *src_parent == *dst_parent) {
		writeLine("serverLog", "pep_resource_rename_post: " ++ IIMETADATAXMLNAME ++ " was renamed to *dst_basename. *src_parent loses user metadata.");
		iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
	} else if (*src_parent != *dst_parent) {
		# The IIMETADATAXMLNAME file was moved to another folder or trashed. Check if src_parent still exists and Remove user metadata.
		if (uuCollectionExists(*src_parent)) {
			iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
			writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent. Remove User Metadata from *src_parent.");
		} else {
			writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent and *src_parent is gone.");
		}
	}
}

# \brief iiMetadataXmlUnregisteredPost
iiMetadataXmlUnregisteredPost(*logicalPath) {
	# writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
	uuChopPath(*logicalPath, *parent, *basename);
	if (uuCollectionExists(*parent)) {
		writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename removed. Removing user metadata from *parent");
		iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
	} else {
		writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename was removed, but *parent is also gone.");
	}			
}
