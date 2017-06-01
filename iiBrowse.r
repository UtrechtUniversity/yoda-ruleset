# \file
# \brief Rules to support the research area browser
# \author    Paul Frederiks
# \copyright Copyright (c) 2015 - 2017 Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

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
# \param[out] result 		JSON output of subcollections and their flags
# \param[out] status            Status code: 'Success' of all ok
# \param[out] statusInfo        Extra information if something went wrong
iiBrowse(*path, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = ''; 
	
	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection){
		*fields = list("COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path));
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
			# Add collection metadata with ilab prefix 	
			uuCollectionMetadataKvp(*coll_id, UUORGMETADATAPREFIX, *kvp);
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
			# Add Dataobject metadata with ilab prefix
			uuObjectMetadataKvp(*data_id, UUORGMETADATAPREFIX, *kvp);
			*kvpList = cons(*kvp, *kvpList);
		}
	}
	*kvpList = cons(hd(*rowList), *kvpList);
	uuKvpList2JSON(*kvpList, *result, *size);

}

# \brief iiCollectionDetails return a json object containing the details of a collection
# \param[in] path      path of collection (COLL_NAME)
# \param[out] result   JSON object containing Details of the Collection
iiCollectionDetails(*path, *result, *status, *statusInfo) {
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

	msiString2KeyValPair("path=*path", *kvp);

	foreach(*row in SELECT COLL_ID, COLL_NAME, COLL_PARENT_NAME, COLL_MODIFY_TIME, COLL_CREATE_TIME WHERE COLL_NAME = *path) {
		*parent = *row.COLL_PARENT_NAME;
		*kvp.parent = *parent;
		*kvp.basename = triml(*path, *parent ++ "/");
		*coll_id = *row.COLL_ID;
		*kvp.id = *coll_id;
		*kvp."irods_type" = "Collection";
		*kvp."coll_create_time" = *row.COLL_CREATE_TIME;
		*kvp."coll_modify_time" = *row.COLL_MODIFY_TIME;
	}



	# The following information is only  applicable inside research groups.
	if (*path like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		*kvp.userMetadata = "true";
		iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager); 
		*kvp.groupName = *groupName;
		*kvp.userType = *userType;
		if (*isDatamanager) {
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

	} else if (*path like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		*metadataXmlName = IIMETADATAXMLNAME;
		*kvp.isVaultPackage = "no";
		foreach(*row in SELECT DATA_ID WHERE COLL_NAME = *path AND DATA_NAME = *metadataXmlName) {
			*kvp.userMetadata = "true";
			*kvp.isVaultPackage = "yes";
		}
		
		*isFound = false;
		# Check Access
		*kvp.researchGroupAccess = "no";
		foreach(*row in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
			*userId = *row.COLL_ACCESS_USER_ID;
			foreach(*row in SELECT USER_NAME WHERE USER_ID = *userId) {
				*userName = *row.USER_NAME;
				if (*userName like "datamanager-*") {
					*isFound = true;
					*datamanagerGroup = *userName;
					uuGroupGetMemberType(*datamanagerGroup, uuClientFullName, *userTypeIfDatamanager);
					if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
						*kvp.isDatamanager = "yes";
					} else {
						*kvp.isDatamanager = "no";
					}
				}
				if (*userName like "research-*") {
					*kvp.researchGroupAccess = "yes";
				}
			}
		}
		if (*isFound) {
		       *kvp.hasDatamanager = "yes";
		} else {
			*kvp.hasDatamanager = "no";
		        *kvp.isDatamanager = "no";	
		}
		
		
		
	}


	uuKvp2JSON(*kvp, *result);
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

