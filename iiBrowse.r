# \file      iiBrowse.r
# \brief     Rules to support the research area browser
# \author    Lazlo Westerhof
# \author    Paul Frederiks
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# ---------------- Start of Yoda FrontOffice API ----------------

# \brief iiFOCollectionDetails return a json object containing the details of a collection
# \param[in] path      path of collection (COLL_NAME)
# \param[out] result   JSON object containing details of the Collection
iiFrontCollectionDetails(*path, *result, *status, *statusInfo) {
	msiString2KeyValPair("", *kvp);

	iiCollectionDetails(*path, *kvp, *status, *statusInfo);
	uuKvp2JSON(*kvp, *result);
}

#---------------- End of Yoda Front Office API ----------------


# \brief orderclause	helper functions to determine order clause
#			defaults to Ascending order
orderclause(*column, *orderby, *ascdesc) = if *column == *orderby then orderdirection(*ascdesc) else ""
orderdirection(*ascdesc) = if *ascdesc == "desc" then "ORDER_DESC" else "ORDER_ASC"

iscollection(*collectionOrDataObject) = if *collectionOrDataObject == "Collection" then true else false

# \brief iiBrowse	        return list of subcollections or dataobjects with ilab specific information attached
# \param[in] path		requested path of parent collection
# \param[in] collectionOrDataObject	Set to "Collection" if you want collections or "DataObject" (Or anything
#				        else) if you want dataobjects
# \param[in] orderby		which column to sort on
# \param[in] ascdesc		Order Ascending or Descending: "asc" or "desc"
# \param[in] limit		limit the list of results. Cast to int
#\ param[in] offset		Start returning results from offset. Cast to int
#\ param[in] space		Research or vault space
# \param[out] result 		JSON output of subcollections and their flags
# \param[out] status            Status code: 'Success' of all ok
# \param[out] statusInfo        Extra information if something went wrong
iiBrowse(*path, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *space, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = '';

	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection){
		*fields = list("COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
                if(*space == "research") {
                        *conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                                           uucondition("COLL_NAME", "not like", "/$rodsZoneClient/home/vault-%"),
                                           uucondition("COLL_NAME", "not like", "/$rodsZoneClient/home/grp-vault-%"));
                } else {
                        *conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                                           uucondition("COLL_NAME", "like", "/$rodsZoneClient/home/%vault-%"));
                }
	} else {
		*fields = list("DATA_ID", "DATA_NAME", "MIN(DATA_CREATE_TIME)", "MAX(DATA_MODIFY_TIME)");
		*conditions =  list(uucondition("COLL_NAME", "=", *path));
	}

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList, *status, *statusInfo);

	if (*status != 'Success') {
		succeed;
	}

	*kvpList = list()
	if (*iscollection) {
		foreach(*row in tl(*rowList)) {
			msiString2KeyValPair("", *kvp);
			*name =	*row.COLL_NAME;
			*kvp."path" = *name;
			*kvp.basename = triml(*name, *path ++ "/");
			*coll_id = *row.COLL_ID;
			*kvp.id = *coll_id;
			*kvp."irods_type" = "Collection";
			*kvp."create_time" = *row.COLL_CREATE_TIME;
			*kvp."modify_time" = *row.COLL_MODIFY_TIME;
			*kvpList = cons(*kvp, *kvpList);
		}
	} else {
		foreach(*row in tl(*rowList)) {
			msiString2KeyValPair("", *kvp);
			*name = *row.DATA_NAME;
			*kvp.basename = *name;
			*kvp."path" = *path ++ "/" ++ *name;
			*data_id = *row.DATA_ID;
			*kvp.id = *data_id;
			*kvp."create_time" = *row.DATA_CREATE_TIME;
			*kvp."modify_time" = *row.DATA_MODIFY_TIME;
			*kvp."irods_type" = "DataObject";
			*kvpList = cons(*kvp, *kvpList);
		}
	}
	*kvpList = cons(hd(*rowList), *kvpList);
	uuKvpList2JSON(*kvpList, *result, *size);

}

# \brief iiCollectionDetails return a key value pair  containing the details of a collection
#
# \param[in] path   path of collection (COLL_NAME)
# \param[out] kvp   key value pair with all required info on current collection (=*path)
iiCollectionDetails(*path, *kvp, *status, *statusInfo) {
        *status = 'Success';
        *statusInfo = '';

        # First check if path exists and fail if not
        if (!uuCollectionExists(*path)) {
                # class USER_INPUT_PATH_ERR(UserInputException):
                # code = -317000
                # fail(-317000);
                *status = 'ErrorPathNotExists';
                *statusInfo = 'The indicated path does not exist';
                succeed;
        }

        uuChopPath(*path, *parent, *baseName);
        *kvp.basename = *baseName;

        if (*path like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
                # Retrieve collection details of research collection.
                iiCollectionDetailsResearch(*path, *kvp);
        } else if (*path like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
                # Retrieve collection details of vault collection.
                iiCollectionDetailsVault(*path, *kvp);
        }
}

# \brief Return a key value pair containing the details of a research collection
#
# \param[in]  path  path of research collection (COLL_NAME)
# \param[out] kvp   key value pair with all required info on current collection (=*path)
iiCollectionDetailsResearch(*path, *kvp) {
        *kvp.userMetadata = "true";

        # Retrieve user group name and user type.
        *groupName = "";
        rule_uu_collection_group_name(*path, *groupName);
        *kvp.groupName = *groupName;

        uuGroupGetMemberType(*groupName, uuClientFullName, *userType);
        *kvp.userType = *userType;

        # Check if user is datamanager.
        uuGroupGetCategory(*groupName, *category, *subcategory);
        uuGroupGetMemberType("datamanager-" ++ *category, uuClientFullName, *userTypeIfDatamanager);
        if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
                *kvp.isDatamanager = "yes";
        } else {
                *kvp.isDatamanager = "no";
        }

        iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, false, *metadataKvpList);
        *folderStatus = FOLDER;
        foreach(*metadataKvp in *metadataKvpList) {
                if (*metadataKvp.attrName == IISTATUSATTRNAME) {
                        *folderStatus = *metadataKvp.attrValue;
                        break;
                }
        }
        *kvp.folderStatus = *folderStatus;

        *lockFound = "no";
        *lockCount = 0;
        foreach(*metadataKvp in *metadataKvpList) {
                if (*metadataKvp.attrName == IILOCKATTRNAME) {
                        *lockCount = *lockCount + 1;
                        *rootCollection = *metadataKvp.attrValue;
                        *kvp.lockRootCollection = *rootCollection;
                        if (*rootCollection == *path) {
                                *lockFound = "here";
                        } else {
                                *children = triml(*rootCollection, *path);
                                if (*children == *rootCollection) {
                                        *ancestors = triml(*path, *rootCollection);
                                        if (*ancestors == *path) {
                                                *lockFound = "outoftree";
                                        } else {
                                                *lockFound = "ancestor";
                                        }
                                } else {
                                        *lockFound = "descendant";
                                }
                        }
                }
        }

        *kvp.lockFound = *lockFound;
        *kvp.lockCount = str(*lockCount);

        # Check if vault is accesible.
        uuChop(*groupName, *_, *baseName, "-", true);
        *vaultName = IIVAULTPREFIX ++ *baseName;
        foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = "/$rodsZoneClient/home/*vaultName") {
                *kvp.vaultPath = *vaultName;
        }
}

# \brief Return a key value pair containing the details of a vault collection
#
# \param[in]  path  path of vault collection (COLL_NAME)
# \param[out] kvp   key value pair with all required info on current collection (=*path)
iiCollectionDetailsVault(*path, *kvp) {
        *vaultStatus = "";
        foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = IIVAULTSTATUSATTRNAME) {
                *vaultStatus = *row.META_COLL_ATTR_VALUE;
        }

        # Check if vault package is currently in state transition.
        *vaultActionPending = "no";
        *vaultActionStatus = UUORGMETADATAPREFIX ++ "vault_status_action_*kvp.id";
        foreach(*row in SELECT COLL_ID WHERE META_COLL_ATTR_NAME = *vaultActionStatus AND META_COLL_ATTR_VALUE = 'PENDING') {
                *vaultActionPending = "yes";
        }

		*kvp.isVaultPackage = "no";
		*kvp.userMetadata = "false";

        if (*vaultStatus == SUBMITTED_FOR_PUBLICATION ||
            *vaultStatus == APPROVED_FOR_PUBLICATION ||
            *vaultStatus == UNPUBLISHED || *vaultStatus == PUBLISHED ||
            *vaultStatus == PENDING_DEPUBLICATION ||
            *vaultStatus == DEPUBLISHED ||
            *vaultStatus == PENDING_REPUBLICATION ||
            *vaultStatus == COMPLETE) {
                *kvp.isVaultPackage = "yes";
                iiGetLatestVaultMetadataXml(*path, *metadataXmlPath, *metadataXmlSize);
                if (*metadataXmlPath != "") {
                        *kvp.userMetadata = "true";
                }

                iiGetLatestVaultMetadataJson(*path, *metadataJsonPath, *metadataJsonSize);
                if (*metadataJsonPath != "") {
                        *kvp.userMetadata = "true";
                }
        }

        *kvp.vaultStatus = *vaultStatus;
        *kvp.vaultActionPending = *vaultActionPending;

        *isFound = false;
        # Check Access
        *kvp.researchGroupAccess = "no";
        *kvp.inResearchGroup = "no";
        foreach(*row in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
                *userId = *row.COLL_ACCESS_USER_ID;
                foreach(*row in SELECT USER_NAME WHERE USER_ID = *userId) {
                        *userName = *row.USER_NAME;
                        if (*userName like "datamanager-*") {
                                *isFound = true;
                                *datamanagerGroup = *userName;
                                uuGroupGetMemberType(*datamanagerGroup, uuClientFullName, *userType);
                                if (*userType == "normal" || *userType == "manager") {
                                        *kvp.isDatamanager = "yes";
                                } else {
                                        *kvp.isDatamanager = "no";
                                }
                        }
                        if (*userName like "research-*") {
                                *kvp.researchGroupAccess = "yes";

                                # Determine if user is member of research group.
                                *researchGroup = *userName;
                                uuGroupUserExists(*researchGroup, uuClientFullName, false, *membership)
                                if (*membership) {
                                        *kvp.inResearchGroup = "yes";
                                }
                        }
                }
        }
        if (*isFound) {
               *kvp.hasDatamanager = "yes";
        } else {
                *kvp.hasDatamanager = "no";
                *kvp.isDatamanager = "no";
        }

        # Check if vault is accesible.
        *pathElems = split(*path, "/");
        *rodsZone = elem(*pathElems, 0);
        *vaultGroup = elem(*pathElems, 2);
        uuChop(*vaultGroup, *_, *baseName, "-", true);
        *researchName = IIGROUPPREFIX ++ *baseName;
        foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = "/$rodsZoneClient/home/*researchName") {
                *kvp.researchPath = *researchName;
        }
}

# \brief iiListLocks
iiListLocks(*path, *offset, *limit, *result, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	iiGetLocks(*path, *locks);
	*total = size(*locks);
	for(*i = 0; *i < *offset;*i = *i + 1) {
		if (size(*locks) == 0) {
			break;
		}
		*locks = tl(*locks);
	}
	*nLocks = size(*locks);
	if (*nLocks == 0) {
		*status = "NoLocksFound";
		*statusInfo = "No Locks Found";
		*more = 0;
		*returned = 0;
		*json_arr = "[]";
	} else if (*nLocks > *limit) {
		*status = "Success";
		*more = *nLocks - *limit;
		*returnedLocks = list();
		for(*i = 0; *i < *limit; *i = *i + 1) {
			*lock = elem(*locks, *i);
			*returnedLocks = cons(*lock, *returnedLocks);
		}
		*returned = *limit;
		uuList2JSON(*returnedLocks, *json_arr);
	} else {
		*status = "Success";
		*returned = size(*locks);
		*more = 0;
		uuList2JSON(*locks, *json_arr);
	}
	*kvp.locks = *json_arr;
	*kvp.total = str(*total);
	*kvp.more = str(*more);
	*kvp.returned = str(*returned);
	uuKvp2JSON(*kvp, *result);
}


# \brief iiCollectionMetadataKvpList
# \param[in] path

iiCollectionMetadataKvpList(*path, *prefix, *strip, *lst) {
	*lst = list();
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *path
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		if (*strip) {
			*kvp.attrName = triml(*row.META_COLL_ATTR_NAME, *prefix);
		} else {
			*kvp.attrName = *row.META_COLL_ATTR_NAME;
		}
		*kvp.attrValue = *row.META_COLL_ATTR_VALUE;
		*lst = cons(*kvp, *lst);
	}
}

# \brief iiDataObjectKvpList
iiDataObjectMetadataKvpList(*path, *prefix, *strip, *lst) {
	*lst = list();
	uuChopPath(*path, *collName, *dataName);
	foreach(*row in SELECT META_DATA_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *collName
		AND DATA_NAME = *dataName
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		if (*strip) {
			*kvp.attrName = triml(*row.META_DATA_ATTR_NAME, *prefix);
		} else {
			*kvp.attrName = *row.META_DATA_ATTR_NAME;
		}
		*kvp.attrValue = *row.META_DATA_ATTR_VALUE;
		*lst = cons(*kvp, *lst);
	}
}
