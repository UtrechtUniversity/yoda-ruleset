# \brief Rules to support the ilab browser
# \author Paul Frederiks

# \brief orderclause	helper functions to determine order clause
#			defaults to Ascending order			
orderclause(*column, *orderby, *ascdesc) = if *column == *orderby then orderdirection(*ascdesc) else ""
orderdirection(*ascdesc) = if *ascdesc == "desc" then "ORDER_DESC" else "ORDER_ASC"

iscollection(*collectionOrDataObject) = if *collectionOrDataObject == "Collection" then true else false

# \brief iiBrowse	return list of subcollections or dataobjects with ilab specific information attached
# \param[in] path		requested path of parent collection
# \param[in] collectionOrDataObject	Set to "Collection" if you want collections or "DataObject" (Or anything else) if you want dataobjects
# \param[in] orderby		which column to sort on 
# \param[in] ascdesc		Order Ascending or Descending: "asc" or "desc"
# \param[in] limit		limit the list of results. Cast to int
#\ param[in] offset		Start returning results from offset. Cast to int
# \param[out] result 		JSON output of subcollections and their flags
iiBrowse(*path, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection){
		*fields = list("COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path));
	} else {
		*fields = list("DATA_ID", "DATA_NAME", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
		*conditions =  list(uucondition("COLL_NAME", "=", *path), uucondition("DATA_NAME", "not like", "\.%"));
	}

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
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
iiCollectionDetails(*path, *result) {

	# First check if path exists and fail if not
	if (!uuCollectionExists(*path)) {
		# class USER_INPUT_PATH_ERR(UserInputException):
		# code = -317000
		fail(-317000);
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



	iiFileCount(*path, *totalSize, *dircount, *filecount, *modified);
	*kvp.dircount = *dircount;
	*kvp.totalSize = *totalSize;
	*kvp.filecount = *filecount;
	*kvp.content_modify_time = *modified;

	iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, true, *kvpList);
	uuKvpList2JSON(*kvpList, *orgMetadata_json, *size);

	*kvp.orgMetadata = *orgMetadata_json;

	# The following information is only  applicable inside research groups.
	if (*path like "/$rodsZoneClient/home/" ++ IIGROUPPREFIX ++ "*") {
		iiCollectionGroupNameAndUserType(*path, *groupName, *userType); 
		*kvp.groupName = *groupName;
		*kvp.userType = *userType;

		*orgStatus = UNPROTECTED;
		foreach(*metadataKvp in *kvpList) {
			if (*metadataKvp.attrName == "status") {
				*orgStatus = *metadataKvp.attrValue;
				break;
			}
		}
		*kvp.folderStatus = *orgStatus;

		*lockFound = "no";
		foreach(*metadataKvp in *kvpList) {
			if (*metadataKvp.attrName like "lock_*") {
				*rootCollection = *metadataKvp.attrValue;
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

	}

	uuKvp2JSON(*kvp, *result);
}

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

