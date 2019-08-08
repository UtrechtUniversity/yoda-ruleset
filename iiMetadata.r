# \file      iiMetadata.r
# \brief     This file contains rules related to metadata to a dataset.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Transform yoda-metadata.xml from versionFrom into versionTo. If at all possible
#
# \param[in]  path        Path of the yoda-metadata.xml
# \param[in]  versionFrom Version within yoda-metadata.xml
# \param[in]  versionTo	  Version yoda-metadata.xml must be converted into
# \param[out] status      Status of the action
# \param[out] statusInfo  Information message when action was not successful
#
iiFrontTransformXml(*path, *status, *statusInfo)
{
        *status = "Success";
        *statusInfo = "";
        *statusPy = "";
        *statusInfoPy = "";
        iiRuleTransformXml(*path, *statusPy, *statusInfoPy);

        *status = *statusPy;
        *statusInfo = *statusInfoPy;
}


# \brief Get the XSD location to be included the metadata form.
#
# \param[in]  folder        Path of the folder
# \param[out] schemaLocation Metadata schema location based upon location of yoda-metadata.xml
# \param[out] status        Status of the action
# \param[out] statusInfo    Information message when action was not successful
#
iiFrontGetSchemaLocation(*folder, *schemaLocation, *status, *statusInfo)
{
        *status = "Success";
        *statusInfo = "";

        *schema = '';

        iiRuleGetLocation(*folder, *schema); # it is not possible to directly use *schemaLocation here

        *schemaLocation =  *schema; # again, does not work when passing schemaLocation direcly in iiRuleGetLocation
}


# \brief Get the XSD location to be included the metadata form.
#
# \param[in]  folder        Path of the folder
# \param[out] schemaSpace   Metadata schema space based upon location of yoda-metadata.xml
# \param[out] status        Status of the action
# \param[out] statusInfo    Information message when action was not successful
#

iiFrontGetSchemaSpace(*folder, *schemaSpace, *status, *statusInfo)
{
        *status = "Success";
        *statusInfo = "";

        *schema = '';

        iiRuleGetSpace(*folder, *schema); # it is not possible to directly use *schemaLocation here

        *schemaSpace =  *schema; # again, does not work when passing schemaLocation direcly in iiRuleGetSpace
}


# \brief Get the JSON metadata schema for the metadata form.
#
# \param[in]  folder        Path of the folder
# \param[out] result        JSON metadata schema
# \param[out] status        Status of the action
# \param[out] statusInfo    Information message when action was not successful
#
iiFrontGetJsonSchema(*folder, *result, *status, *statusInfo)
{
        *status = "Unknown";
        *statusInfo = "";

        *jsonPath = "";
        *pathElems = split(*folder, '/');
        *rodsZone = elem(*pathElems, 0);
        *groupName = elem(*pathElems, 2);

        # Get category name.
        uuGetBaseGroup(*groupName, *baseName);
        uuGroupGetCategory(*baseName, *category, *subcategory);
        *jsonColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
        *jsonName = IIJSONNAME;

        # Check if category schema is used.
        *categorySchema = false;
        foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *jsonColl AND DATA_NAME = *jsonName) {
               *categorySchema = true;
        }
        if (!*categorySchema) {
                *jsonColl = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME
        }

	# Retrieve schema path and data size.
        foreach(*row in SELECT COLL_NAME, DATA_NAME, DATA_SIZE WHERE COLL_NAME = *jsonColl AND DATA_NAME = *jsonName) {
               *jsonPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	       *dataSize = *row.DATA_SIZE;
        }

	# Open JSON schema.
	*err = errorcode(msiDataObjOpen("objPath=*jsonPath", *fd));
	if (*err < 0) {
		writeLine("serverLog", "iiFrontGetJsonSchema: Opening *jsonPath failed with errorcode: *err");
		*status = "PermissionDenied";
		*statusInfo = "Could not open JSON schema.";
		succeed;
	}

	# Read JSON schema.
	*err1 = errorcode(msiDataObjRead(*fd, *dataSize, *buf));
	*err2 = errorcode(msiDataObjClose(*fd, *status));
	*err3 = errorcode(msiBytesBufToStr(*buf, *result));
	if (*err1 == 0 && *err2 == 0 && *err3 == 0) {
		*status = "Success";
	} else {
		writeLine("serverLog", "iiFrontGetJsonSchema: Reading *jsonPath failed with errorcode: *err1, *err2, *err3.");
		*status = "ReadFailure";
		*statusInfo = "Failed to read JSON schema from disk.";
	}
}


# \brief Get the JSON UI schema for the metadata form.
#
# \param[in]  folder        Path of the folder
# \param[out] result        JSON UI schema
# \param[out] status        Status of the action
# \param[out] statusInfo    Information message when action was not successful
#
iiFrontGetJsonUiSchema(*folder, *result, *status, *statusInfo)
{
        *status = "Unknown";
        *statusInfo = "";

        *jsonPath = "";
        *pathElems = split(*folder, '/');
        *rodsZone = elem(*pathElems, 0);
        *groupName = elem(*pathElems, 2);

        # Get category name.
        uuGetBaseGroup(*groupName, *baseName);
        uuGroupGetCategory(*baseName, *category, *subcategory);
        *jsonColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
        *jsonName = IIJSONUINAME;


        # Check if category schema is used.
        *categorySchema = false;
        foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *jsonColl AND DATA_NAME = *jsonName) {
               *categorySchema = true;
        }
        if (!*categorySchema) {
                *jsonColl = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME
        }

	# Retrieve schema path and data size.
        foreach(*row in SELECT COLL_NAME, DATA_NAME, DATA_SIZE WHERE COLL_NAME = *jsonColl AND DATA_NAME = *jsonName) {
               *jsonPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	       *dataSize = *row.DATA_SIZE;
        }

	# Open JSON schema.
	*err = errorcode(msiDataObjOpen("objPath=*jsonPath", *fd));
	if (*err < 0) {
		writeLine("serverLog", "iiFrontGetJsonSchema: Opening *jsonPath failed with errorcode: *err");
		*status = "PermissionDenied";
		*statusInfo = "Could not open JSON UI schema.";
		succeed;
	}

	# Read JSON schema.
	*err1 = errorcode(msiDataObjRead(*fd, *dataSize, *buf));
	*err2 = errorcode(msiDataObjClose(*fd, *status));
	*err3 = errorcode(msiBytesBufToStr(*buf, *result));
	if (*err1 == 0 && *err2 == 0 && *err3 == 0) {
		*status = "Success";
	} else {
		writeLine("serverLog", "iiFrontGetJsonUiSchema: Reading *jsonPath failed with errorcode: *err1, *err2, *err3.");
		*status = "ReadFailure";
		*statusInfo = "Failed to read JSON schema from disk.";
	}
}


# \brief Locate the research XSD to use for a metadata path.
#
# \param[in] metadataXmlPath path of the metadata XML file that needs to be validated
# \param[out] xsdPath        path of the research XSD to use for validation
#
iiGetResearchXsdPath(*metadataXmlPath, *xsdPath) {
	if (*metadataXmlPath == "") {
		*xsdPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IIRESEARCHXSDNAME;
	} else {
                *xsdPath = "";
                *pathElems = split(*metadataXmlPath, '/');
                *rodsZone = elem(*pathElems, 0);
                *groupName = elem(*pathElems, 2);

                uuGroupGetCategory(*groupName, *category, *subcategory);
                *xsdColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
                *xsdName = IIRESEARCHXSDNAME;
                foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdColl AND DATA_NAME = *xsdName) {
                       *xsdPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
                }

                if (*xsdPath == "") {
		        *xsdPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IIRESEARCHXSDNAME;
                }
	}
}

# \brief Locate the vault XSD to use for a metadata path.
#
# \param[in] metadataXmlPath path of the metadata XML file that needs to be validated
# \param[out] xsdPath        path of the vault XSD to use for validation
#
iiGetVaultXsdPath(*metadataXmlPath, *xsdPath) {
	if (*metadataXmlPath == "") {
		*xsdPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" IIDEFAULTSCHEMANAME ++ "/" ++ IIVAULTXSDNAME;
	} else {
                *xsdPath = "";
                *pathElems = split(*metadataXmlPath, '/');
                *rodsZone = elem(*pathElems, 0);
                *groupName = elem(*pathElems, 2);

                uuGroupGetCategory(*groupName, *category, *subcategory);
                *xsdColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
                *xsdName = IIVAULTXSDNAME;
                foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdColl AND DATA_NAME = *xsdName) {
                       *xsdPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
                }

                if (*xsdPath == "") {
		        *xsdPath = "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IIVAULTXSDNAME;
                }
	}
}


# \brief Locate the XSL to use for a metadata path.
#
# \param[in] metadataXmlPath path of the metadata XML file that needs to be converted
# \param[out] xslPath        path of the XSL to use for conversion to an AVU XML
#
iiGetXslPath(*metadataXmlPath, *xslPath) {
	*xslPath = "";
	*pathElems = split(*metadataXmlPath, '/');
	*rodsZone = elem(*pathElems, 0);
	*groupName = elem(*pathElems, 2);

	uuGroupGetCategory(*groupName, *category, *subcategory);
	*xslColl = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ *category;
	*xslName = IIAVUXSLNAME;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslColl AND DATA_NAME = *xslName) {
		*xslPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}

	if (*xslPath == "") {
		*xslPath = "/*rodsZone" ++ IISCHEMACOLLECTION ++ "/" ++ IIDEFAULTSCHEMANAME ++ "/" ++ IIAVUXSLNAME;
	}
}


# \brief Validate XML against XSD schema.
#
# \param[in] metadataXmlPath path of the metadata XML file that needs to be converted
# \param[out] xsdPath        path of the vault XSD to use for validation
# \param[out] err            Zero is valid XML, negative is microservice error, positive is invalid XML
#
iiValidateXml(*metadataXmlPath, *xsdPath, *invalid, *msg) {
    *invalid = 0;
    *err = errormsg(msiXmlDocSchemaValidate(*metadataXmlPath, *xsdPath, *statusBuf), *msg);
    if (*err < 0) {
            *invalid = 1;
    } else {
            # Output in status buffer means XML is not valid.
            msiBytesBufToStr(*statusBuf, *statusStr);
            *len = strlen(*statusStr);
            if (*len == 0) {
                    #DEBUG writeLine("serverLog", "iiValidateXML: *metadataXmlPath validates");
            } else {
                    #DEBUG writeLine("serverLog", "iiValidateXML: *metadataXmlPath - *statusStr");
                    *invalid = 1;
        }
}
}


# \brief Return info needed for the metadata form.
#
# \param[in] path       path of the collection where metadata needs to be viewed or added
# \param[out] result    json object with the location of the metadata file,
#                       the XSD and the role of the current user in the group
#
iiPrepareMetadataForm(*path, *result) {
        # Research space
        if (*path like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
                msiString2KeyValPair("", *kvp);
                *kvp.isVaultPackage = "no";

                # Retrieve user group name and user type.
                iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager);
                *kvp.groupName = *groupName;
                *kvp.userType = *userType;
                if (*isDatamanager) {
                        *kvp.isDatamanager = "yes";
                } else {
                        *kvp.isDatamanager = "no";
                }

                # Retrieve metadata on collection.
                iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, false, *kvpList);

                # Get folder status.
                *orgStatus = FOLDER;
                foreach(*metadataKvp in *kvpList) {
                        if (*metadataKvp.attrName == IISTATUSATTRNAME) {
                                *orgStatus = *metadataKvp.attrValue;
                                break;
                        }
                }
                *kvp.folderStatus = *orgStatus;

                # Check for locks on the collection and ancestor / descendant collections.
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

                # Retrieve yoda-metadata.xml path.
                *xmlname = IIMETADATAXMLNAME;
                *xmlpath = "";
                foreach(*row in SELECT COLL_NAME, DATA_NAME
                                WHERE COLL_NAME = *path
                                  AND DATA_NAME = *xmlname) {
                        *xmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
                }

                if (*xmlpath == "") {
                        *kvp.hasMetadataXml = "false";
                        *kvp.metadataXmlPath = *path ++ "/" ++ IIMETADATAXMLNAME;
                } else {
                        *kvp.hasMetadataXml = "true";
                        *kvp.metadataXmlPath = *xmlpath;
                        # Check for locks on metadata XML.
                        iiDataObjectMetadataKvpList(*path, IILOCKATTRNAME, true, *metadataXmlLocks);
                        uuKvpList2JSON(*metadataXmlLocks, *json_str, *size);
                        *kvp.metadataXmlLocks = *json_str;
                }

                # Retrieve category information.
                uuGroupGetCategory(*groupName, *category, *subcategory);
                *kvp.category = *category;
                *kvp.subcategory = *subcategory;

                # Check if parent metadata XML exists and is valid.
                iiGetResearchXsdPath(*xmlpath, *xsdPath);
                uuChopPath(*path, *parent, *child);
                *kvp.parentHasMetadataXml = "false";
                foreach(*row in SELECT DATA_NAME, COLL_NAME
                                WHERE COLL_NAME = *parent
                                  AND DATA_NAME = *xmlname) {
                        *parentxmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
                        iiValidateXml(*parentxmlpath, *xsdPath, *err, *msg);
                        if (*err < 0) {
                                writeLine("serverLog", *msg);
                        } else if (*err == 0) {
                                *kvp.parentHasMetadataXml = "true";
                                *kvp.parentMetadataXmlPath = *parentxmlpath;
                        } else {
                                writeLine("serverLog", "iiPrepareMetadataForm: *msg");
                        }
                }

                # Check for transformations.
                *kvp.transformation = "false";
                *kvp.transformationText = "";
                if (*xmlpath != "") {
                        *transformation = '';
                        *transformationText = '';
                        iiRulePossibleTransformation(*xmlpath, *transformation, *transformationText)
                        *kvp.transformation = *transformation;
                        *kvp.transformationText = *transformationText;
                }

                uuKvp2JSON(*kvp, *result);
        # Vault space.
        } else if (*path like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
                *pathElems = split(*path, "/");
                *rodsZone = elem(*pathElems, 0);
                *vaultGroup = elem(*pathElems, 2);
                uuJoin("/", tl(tl(tl(*pathElems))), *vaultPackageSubPath);

                msiString2KeyValPair("", *kvp);
                *kvp.groupName = *vaultGroup;
                uuGroupGetMemberType(uuClientFullName, *vaultGroup, *memberType);
                *kvp.userType = *memberType;

                # Retrieve vault package status.
                *vaultStatusAttrName = IIVAULTSTATUSATTRNAME;
                *vaultStatus = "";
                foreach(*row in SELECT META_COLL_ATTR_VALUE
                                WHERE COLL_NAME = *path
                                  AND META_COLL_ATTR_NAME = *vaultStatusAttrName) {
                        *vaultStatus = *row.META_COLL_ATTR_VALUE;
                }

                if (*vaultStatus == SUBMITTED_FOR_PUBLICATION ||
                    *vaultStatus == APPROVED_FOR_PUBLICATION ||
                    *vaultStatus == UNPUBLISHED || *vaultStatus == PUBLISHED ||
                    *vaultStatus == PENDING_DEPUBLICATION ||
                    *vaultStatus == DEPUBLISHED ||
                    *vaultStatus == PENDING_REPUBLICATION ||
                    *vaultStatus == COMPLETE) {
                        *kvp.isVaultPackage = "yes";
                } else {
                        *kvp.isVaultPackage = "no";
                }

                # Retrieve category information.
                uuGetBaseGroup(*vaultGroup, *baseGroup);
                uuGroupGetCategory(*baseGroup, *category, *subcategory);
                *kvp.category = *category;
                *kvp.subcategory = *subcategory;

                # Check is user is datamanager.
                uuGroupExists("datamanager-*category", *datamanagerExists);
                if (!*datamanagerExists) {
                        *isDatamanager = false;
                } else {
                        uuGroupGetMemberType("datamanager-*category", uuClientFullName, *userTypeIfDatamanager);
                        if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
                                *isDatamanager = true;
                        } else {
                                *isDatamanager = false;
                        }
                }
                if (*isDatamanager) {
                        *kvp.isDatamanager = "yes";
                } else {
                        *kvp.isDatamanager = "no";
                }

                # Retrieve latest version of the metadata XML.
                iiGetLatestVaultMetadataXml(*path, *metadataXmlPath, *metadataXmlSize);
                if (*metadataXmlPath == "") {
                        *hasMetadataXml = false;
                        *kvp.hasMetadataXml = "no";
                } else {
                        *hasMetadataXml = true;
                        *kvp.hasMetadataXml = "yes";
                        *kvp.metadataXmlPath = *metadataXmlPath;
                }

                # Check if a shadow metadata XML exists
                if (*isDatamanager && *hasMetadataXml) {
                        *shadowMetadataXml = "/*rodsZone/home/datamanager-*category/*vaultGroup/*vaultPackageSubPath/" ++ IIMETADATAXMLNAME;
                        *kvp.hasShadowMetadataXml = "no";
                        if (uuFileExists(*shadowMetadataXml)) {
                                *kvp.hasShadowMetadataXml = "yes";
                                iiDataObjectMetadataKvpList(*shadowMetadataXml, UUORGMETADATAPREFIX, true, *kvpList);
                                foreach(*item in *kvpList) {
                                        if (*item.attrName == "cronjob_vault_ingest") {
                                                *kvp.vaultIngestStatus = *item.attrValue;
                                        }
                                        if (*item.attrName == "cronjob_vault_ingest_info") {
                                                *kvp.vaultIngestStatusInfo = *item.attrValue;
                                        }
                                }

                        }
                }

                # Read only metadata form when publication is pending.
                if (*vaultStatus == APPROVED_FOR_PUBLICATION ||
                    *vaultStatus == PENDING_DEPUBLICATION ||
                    *vaultStatus == PENDING_REPUBLICATION) {
                        *kvp.userType = "reader";
                        *kvp.isDatamanager = "no";
                }

                uuKvp2JSON(*kvp, *result);
        } else {
                *result = "";
        }
}

# \brief Remove the yoda-metadata.xml file and remove all user metadata from irods.
#
# \param[in] path		Path of collection to scrub of metadata
#
iiRemoveAllMetadata(*path) {
	*metadataxmlpath =  *path ++ "/" ++ IIMETADATAXMLNAME;
	msiAddKeyValToMspStr("objPath", *metadataxmlpath, *options);
	msiAddKeyValToMspStr("forceFlag", "", *options);
	*err = errorcode(msiDataObjUnlink(*options, *status));
	if (*err < 0) {
		writeLine("serverLog", "iiRemoveMetadata *path returned errorcode: *err");
	}
}

# \brief Remove the User AVU's from the irods AVU store.
#
# \param[in] coll	    Collection to scrub of user metadata
# \param[in] prefix	    prefix of metadata to remov
#
iiRemoveAVUs(*coll, *prefix) {
	#DEBUG writeLine("serverLog", "iiRemoveAVUs: Remove all AVU's from *coll prefixed with *prefix");
	msiString2KeyValPair("", *kvp);
	*prefix = *prefix ++ "%";

	*duplicates = list();
	*prev = "";
	foreach(*row in SELECT order_asc(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		if (*attr == *prev) {
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Duplicate attribute " ++ *attr);
		       *duplicates = cons((*attr, *val), *duplicates);
		} else {
			msiAddKeyVal(*kvp, *attr, *val);
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
			*prev = *attr;
		}
	}

	msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");

	foreach(*pair in *duplicates) {

		(*attr, *val) = *pair;
		#DEBUG writeLine("serverLog", "iiRemoveUserAVUs: Duplicate key Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *attr, *val);
		msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	}
}

# \brief Ingest user metadata from XML preprocessed with an XSLT.
#
# \param[in] metadataxmlpath	path of metadataxml to ingest
# \param[in] xslpath		path of XSL stylesheet
#
iiImportMetadataFromXML (*metadataxmlpath, *xslpath) {
	#DEBUG writeLine("serverLog", "iiImportMetadataFromXML: calling msiXstlApply '*xslpath' '*metadataxmlpath'");
	# apply xsl stylesheet to metadataxml
	msiXsltApply(*xslpath, *metadataxmlpath, *buf);
	#DEBUG writeBytesBuf("serverLog", *buf);

	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	#DEBUG writeLine("serverLog", "iiImportMetdataFromXML: Calling msiLoadMetadataFromXml");
	*err = errormsg(msiLoadMetadataFromXml(*metadataxml_coll, *buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiImportMetadataFromXML: *err - *msg ");
	} else {
		writeLine("serverLog", "iiImportMetadataFromXML: Succesfully loaded metadata from *metadataxmlpath");
	}
}

# \brief Clone metadata file from one place to the other.
#
# \param[in] *src	path of source metadataxml
# \param[in] *dst	path of destination metadataxml
#
iiCloneMetadataXml(*src, *dst) {
	writeLine("serverLog", "iiCloneMetadataXml:*src -> *dst");
	*err = errormsg(msiDataObjCopy(*src, *dst, "", *status), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiCloneMetadataXml: *err - *msg)");
	}
}

# \brief iiMetadataXmlModifiedPost
#
# \param[in] xmlPath
# \param[in] userName
# \param[in] userZone
#
iiMetadataXmlModifiedPost(*xmlPath, *userName, *userZone) {
	if (*xmlPath like regex "/*userZone/home/datamanager-[^/]+/vault-[^/]+/.*/" ++ IIMETADATAXMLNAME ++ "$") {
		 msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_vault_ingest=" ++ CRONJOB_PENDING, *kvp);
		 msiSetKeyValuePairsToObj(*kvp, *xmlPath, "-d");
		 iiAdminVaultIngest();
	} else {
		uuChopPath(*xmlPath, *parent, *basename);
		#DEBUG writeLine("serverLog", "iiMetadataXmlModifiedPost: *basename added to *parent. Import of metadata started");
		iiGetResearchXsdPath(*xmlPath, *xsdPath);
		iiValidateXml(*xmlPath, *xsdPath, *err, *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
		} else if (*err == 0) {
			#DEBUG writeLine("serverLog", "XSD validation successful. Start indexing");
			iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
			iiGetXslPath(*xmlPath, *xslPath);
			iiImportMetadataFromXML(*xmlPath, *xslPath);
		} else {
			writeLine("serverLog", "iiMetadataXmlModifiedPost: Validation report of *xmlPath below.");
			writeLine("serverLog", *msg);
		}
	}
}

# \brief Perform a vault ingest as rodsadmin.
#
iiAdminVaultIngest() {
	msiExecCmd("admin-vaultingest.sh", uuClientFullName, "", "", 0, *out);
}

# \brief iiLogicalPathFromPhysicalPath
#
# \param[in]  physicalPath
# \param[out] logicalPath
# \param[in]  zone
#
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
	#DEBUG writeLine("serverLog", "iiLogicalPathFromPhysicalPath: *physicalPath => *logicalPath");
}

# \brief iiMetadataXmlRenamedPost
#
# \param[in]  src
# \param[in]  dst
# \param[in]  zone
#
iiMetadataXmlRenamedPost(*src, *dst, *zone) {
	uuChopPath(*src, *src_parent, *src_basename);
	# the logical_path in $KVPairs is that of the destination
	uuChopPath(*dst, *dst_parent, *dst_basename);
	if (*dst_basename != IIMETADATAXMLNAME && *src_parent == *dst_parent) {
		#DEBUG writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was renamed to *dst_basename. *src_parent loses user metadata.");
		iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
	} else if (*src_parent != *dst_parent) {
		# The IIMETADATAXMLNAME file was moved to another folder or trashed. Check if src_parent still exists and Remove user metadata.
		if (uuCollectionExists(*src_parent)) {
			iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
			#DEBUG writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent. Remove User Metadata from *src_parent.");
		} else {
			nop; # Empty else clauses fail
			#DEBUG writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent and *src_parent is gone.");
		}
	}
}

# \brief iiMetadataXmlUnregisteredPost
#
# \param[in]  logicalPath
#
iiMetadataXmlUnregisteredPost(*logicalPath) {
	# writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
	uuChopPath(*logicalPath, *parent, *basename);
	if (uuCollectionExists(*parent)) {
		#DEBUG writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename removed. Removing user metadata from *parent");
		iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
	} else {
		#DEBUG writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename was removed, but *parent is also gone.");
	}
}

# \brief iiPrepareVaultMetadataForEditing
#
# \param[in]  metadataXmlPath
# \param[out] tempMetadataXmlPath
# \param[out] status
# \param[out] statusInfo
#
iiPrepareVaultMetadataForEditing(*metadataXmlPath, *tempMetadataXmlPath, *status, *statusInfo) {
	# path of metadataxml in vault:
	# /nluu1dev/home/vault-groupName/path/to/vaultPackage/yoda-metadata[123456789].xml
	# /0       /1   /2              /(3)/(4)/(5)         /(6)
	*status =  "Unknown";
	*statusInfo = "An internal error has occurred";
	*tempMetadataXmlPath = "";
	*pathElems = split(*metadataXmlPath, "/");
	*rodsZone = elem(*pathElems, 0);
	*vaultGroup = elem(*pathElems, 2);
	uuJoin("/", tl(tl(tl(*pathElems))), *metadataXmlSubPath);

	*vaultPackageSubPath = trimr(*metadataXmlSubPath, "/");
	iiDatamanagerGroupFromVaultGroup(*vaultGroup, *datamanagerGroup);
	if (*datamanagerGroup == "") {
		fail;
	}
	*metadataXmlName = IIMETADATAXMLNAME;
	*tempPath = "/*rodsZone/home/*datamanagerGroup/*vaultGroup/*vaultPackageSubPath";

	if (!uuCollectionExists(*tempPath)) {
		*err = errorcode(msiCollCreate(*tempPath, 1, *status));
		if (*err < 0) {
			*status = "FailedToCreateCollection";
			*statusInfo = "Failed to create a staging area at *tempPath";
			succeed;
		}
	}

	*tempMetadataXmlPath = *tempPath ++ "/" ++ IIMETADATAXMLNAME;
	#DEBUG writeLine("serverLog", "iiPrepareVaultMetadataForEditing: *tempMetadataXmlPath");
	*status = "Success";
	*statusInfo = "";

}

# \brief Ingest changes to metadata in to the vault.
#
# \param[in]  metadataXmlPath    path of metadata xml to ingest
# \param[out] status
# \param[out] statusInfo
#
iiIngestDatamanagerMetadataIntoVault(*metadataXmlPath, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";

	# Changes to metadata should be written to the datamanagers area first
	# Example path: /nluu1dev/home/datamanager-category/vault-group/path/to/vaultPackage/yoda-metadata.xml
	# index:        /0       /1   /2                   /3          /(4)/(5)/(6)         /(7)
	*pathElems = split(*metadataXmlPath, "/");
	*rodsZone = elem(*pathElems, 0);
	*datamanagerGroup = elem(*pathElems, 2);
	uuChop(*datamanagerGroup, *_, *category, "-", true);
	*vaultGroup = elem(*pathElems, 3);
	uuJoin("/", tl(tl(tl(tl(*pathElems)))), *metadataXmlSubPath);

	*vaultPackageSubPath = trimr(*metadataXmlSubPath, "/");

	*vaultPackagePath = "/*rodsZone/home/*vaultGroup/" ++ *vaultPackageSubPath;

	if (!uuCollectionExists(*vaultPackagePath)) {
		*status = "VaultPackageMissing";
		*statusInfo = "*vaultPackagePath does not exist";
		succeed;
	}

	# The actor (active datamanager) is registered as DATA_OWNER_NAME on the metadata xml
	# We need this information for the action log.
	uuChopPath(*metadataXmlPath, *collName, *dataName);
	foreach (*row in SELECT DATA_OWNER_NAME WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
		*actor = *row.DATA_OWNER_NAME;
	}

	# Ensure access to the metadata xml for rodsadmin
	msiCheckAccess(*metadataXmlPath, "modify object", *modifyAccess);
	if (*modifyAccess != 1) {
		msiSetACL("default", "admin:own", uuClientFullName, *metadataXmlPath);
	}

	# Generate a new metadata xml filename with a timestamp, to prevent overwriting the old version
	msiGetIcatTime(*timestamp, "unix");
	*timestamp = triml(*timestamp, "0");
	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*vaultMetadataTarget = "*vaultPackagePath/*baseName[*timestamp].*extension";
	*i = 0;
	while (uuFileExists(*vaultMetadataTarget)) {
		*i = *i + 1;
		*vaultMetadataTarget = "*vaultPackagePath/*baseName[*timestamp][*i].*extension";

	}

	iiGetVaultXsdPath(*metadataXmlPath, *xsdPath);
	iiValidateXml(*metadataXmlPath, *xsdPath, *err, *msg);
	if (*err < 0) {
		*status = "FailedToValidateXML";
		*statusInfo = "*err - *msg";
		succeed;
	} else if (*err > 0) {
		*status = "InvalidXML";
		*statusInfo = "*msg";
		succeed;
	}

	*err = errorcode(msiDataObjCopy(*metadataXmlPath, *vaultMetadataTarget, "verifyChksum=", *statusBuf));
	if (*err < 0) {
		*status = "FailedToCopyXML";
		*statusInfo = "Copy to vault failed from *metadataXmlPath to *vaultMetadataTarget with errorcode *err";
		succeed;
	}

	*err = errorcode(iiCopyACLsFromParent(*vaultMetadataTarget, "default"));
	if (*err < 0) {
		*status = "FailedToSetACLs";
		*statusInfo = "Failed to set vault permissions to *vaultMetadataTarget";
		succeed;
	}

	*err = errorcode(iiRemoveAVUs(*vaultPackagePath, UUUSERMETADATAPREFIX));
	if (*err < 0) {
		*status = "FailedToRemoveMetadata";
		*statusInfo = "Failed to remove old metadata from *vaultPackagePath";
		succeed;
	}

        iiGetXslPath(*vaultMetadataTarget, *xslPath);
	*err = errorcode(iiImportMetadataFromXML(*vaultMetadataTarget, *xslPath));
	if (*err < 0) {
		*status = "FailedToImportMetadata";
		*statusInfo = "Failed to ingest new metadata for *vaultPackagePath into index";
		succeed;
	}

	iiAddActionLogRecord(*actor, *vaultPackagePath, "modified metadata");
	iiWriteProvenanceLogToVault(*vaultPackagePath);

	# Add action log record
	#DEBUG writeLine("serverLog", "iiIngestDatamanagerMetadataIntoVault: Removing metadata xml from datamanager folder");
	*err = errorcode(msiDataObjUnlink("objPath=*metadataXmlPath++++forceFlag=", *statusBuf));
	if (*err < 0) {
		*status = "FailedToRemoveDatamanagerXML";
		*statusInfo = "Failed to remove *metadataXmlPath";
		succeed;
	}

	# Cleanup collection created for this process
	*collToRemove = "/*rodsZone/home/*datamanagerGroup/*vaultGroup";
	# Check if no data is left
	*empty = true;
	foreach(*row in SELECT DATA_ID WHERE COLL_NAME like "*collToRemove/%") {
		*empty = false;
	}
	foreach(*row in SELECT DATA_ID WHERE COLL_NAME = *collToRemove) {
		*empty = false;
	}

	if (*empty) {
		*datamanagerFolder = "/*rodsZone/home/*datamanagerGroup";
		msiCheckAccess(*datamanagerFolder, "delete object", *deleteAccess);
		if (*deleteAccess == 0) {
			msiSetACL("recursive", "admin:own", uuClientFullName, *datamanagerFolder);
		}
		*err = errorcode(msiRmColl(*collToRemove, "forceFlag=",*statusBuf));
		if (*err < 0) {
			*status = "FailedToRemoveColl";
			*statusInfo = "Failed to remove *collToRemove";
			succeed;
		}
	} else {
		writeLine("serverLog", "iiIngestDatamanagerMetadataIntoVault: Could not remove *collToRemove as it is not empty");
	}

	# Only update publication if package is published.
	iiVaultStatus(*vaultPackagePath, *vaultStatus);
	if (*vaultStatus != PUBLISHED) {
	   *status = "Success";
	   *statusInfo = "";
	   succeed;
	}

	# Add publication update status to vault package.
	# Also used in frontend to check if vault package metadata update is pending.
	*publicationUpdate = UUORGMETADATAPREFIX ++ "cronjob_publication_update=" ++ CRONJOB_PENDING;
	msiString2KeyValPair(*publicationUpdate, *kvp);
	*err = errormsg(msiAssociateKeyValuePairsToObj(*kvp, *vaultPackagePath, "-C"), *msg);
	if (*err < 0) {
		*status = "FailedToSetPublicationUpdateStatus";
		*statusInfo = "Failed to set publication update status on *vaultPackagePath";
		succeed;
	}
	*err = errorcode(iiSetUpdatePublicationState(*vaultPackagePath, *statusBuf));
	if (*err < 0) {
		*status = "FailedToSetPublicationUpdateStatus";
		*statusInfo = "Failed to set publication update status on *vaultPackagePath";
		succeed;
	}

	*status = "Success";
	*statusInfo = "";
}

# \brief iiGetLatestVaultMetadataXml
#
# \param[in] vaultPackage
# \param[out] metadataXmlPath
#
iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath, *metadataXmlSize) {
	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*dataNameQuery = "%*baseName[%].*extension";
	*dataName = "";
	*metadataXmlPath = "";
	foreach (*row in SELECT DATA_NAME, DATA_SIZE WHERE COLL_NAME = *vaultPackage AND DATA_NAME like *dataNameQuery) {
		if (*dataName == "" || (*dataName < *row.DATA_NAME && strlen(*dataName) <= strlen(*row.DATA_NAME))) {
			*dataName = *row.DATA_NAME;
			*metadataXmlPath = *vaultPackage ++ "/" ++ *dataName;
			*metadataXmlSize = int(*row.DATA_SIZE);
		}
	}
}
