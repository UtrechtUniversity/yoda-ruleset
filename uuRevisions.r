# \file
# \brief Revision management
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#####################################################
#
# \brief uuRevisionCreateAsynchronously  Asynchronous call to uuRevisionCreate
# \param[in] path	The path of the added or modified file.
uuRevisionCreateAsynchronously(*path) {
	remote("localhost", "") {
		delay("<PLUSET>1s</PLUSET>") {
			uuRevisionCreate(*path, *id);
			writeLine("serverLog", "uuRevisionCreate: Revision created for *path ID=*id");
		}
	}
}

# \brief uuRevisionCreate create a revision of a dataobject in a revision folder
# \param[in] path		path of data object to create a revision for
# \param[out] id		object id of revision
uuRevisionCreate(*path, *id) {
	#| writeLine("stdout", "Create a revision of a file");
	#| writeLine("stdout", "Current User: $userNameClient");
	# Step 1: Check requisites:
	# - path should return a dataObject
	*id = "";
	uuChopPath(*path, *parent, *basename);
       #| writeLine("stdout", *timestamp);
	*objectId = 0;
	*found = false;
	foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID WHERE DATA_NAME = *basename AND COLL_NAME = *parent) {
		if (!*found) {
       #| 		writeLine("stdout", *row);
			*found = true;
			*dataId = *row.DATA_ID;
			*modifyTime = *row.DATA_MODIFY_TIME;
			*dataSize = *row.DATA_SIZE;
			*collId = *row.COLL_ID;
			*dataOwner = *row.DATA_OWNER_NAME;
		} else {
			failmsg(-1, "Multiple results for path found");
		}
	}

	if (!*found) {
		failmsg(-317000, "DataObject was not found or path was collection");
	}


	if (int(*dataSize)>500048576) {
		failmsg(-311000, "Files larger than 500MiB cannot store revisions");
	}	


	foreach(*row in SELECT USER_NAME, USER_ZONE WHERE DATA_ID = *dataId AND USER_TYPE = "rodsgroup" AND DATA_ACCESS_NAME = "own") {
	       *groupName = *row.USER_NAME;
		*userZone = *row.USER_ZONE;
	}

	uuLockExists(*parent, *isLocked);
	if (*isLocked) {
		failmsg(-818000, "Collection *parent is Locked");
	}

	*revisionStore = "/*userZone/revisions/*groupName";

	foreach(*row in SELECT COUNT(COLL_ID) WHERE COLL_NAME = *revisionStore) {
	       	*revisionStoreExists = bool(int(*row.COLL_ID));
       	}

	if (*revisionStoreExists) {
		msiGetIcatTime(*timestamp, "icat");
		*iso8601 = timestrf(datetime(int(*timestamp)), "%Y%m%dT%H%M%S%z");
		*revFileName = *basename ++ "_" ++ *iso8601 ++ *dataOwner;
		*revColl = *revisionStore ++ "/" ++ *collId;
		*revPath = *revColl ++ "/" ++ *revFileName;
		*err = errorcode(msiDataObjCopy(*path, *revPath, "verifyChksum=", *msistatus));
		if (*err < 0) {
			if (*err == -312000) {
			# -312000 OVERWRITE_WITHOUT_FORCE_FLAG
				writeLine("serverLog", "uuRevisionCreate: *revPath already exists. This means that *basename was changed multiple times within the same second.");
			} else if (*err == -814000) {
			# -814000 CAT_UNKNOWN_COLLECTION
				writeLine("serverLog", "uuRevisionCreate: Could not access or create *revColl. Please check permissions");
			} else {
				failmsg(*err, "uuRevisionCreate failed");
			}
		} else {
			foreach(*row in SELECT DATA_ID WHERE DATA_NAME = *revFileName AND COLL_NAME = *revColl) {
				*id = *row.DATA_ID;
			}

			msiString2KeyValPair("", *revkv);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_path", *path);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_name", *parent);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_name", *basename);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_owner_name", *dataOwner);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_id", *dataId);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_id", *collId);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_group_name", *groupName);


			msiAssociateKeyValuePairsToObj(*revkv, *revPath, "-d");
		}

	} else {
		failmsg(-814000, "*revisionStore does not exists or is inaccessible for current client.");
	}
}


# \brief uuRevisionRemove
# \param[in] revision_id
uuRevisionRemove(*revision_id) {
	*isfound = false;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revision_id" AND COLL_NAME like "/$rodsZoneClient/revisions/%") {
		if (!*isfound) {
			*isfound = true;
			*objPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
			*args = "";
			msiAddKeyValToMspStr("objPath", *objPath, *args);
			msiAddKeyValToMspStr("forceFlag", "", *args);
			msiDataObjUnlink(*args, *status);
		} else {
			failmsg(-54000, "revision_id returned multiple results");
		}
	}
	if (*isfound) {
		writeLine("serverLog", "uuRevisionRemove('*revision_id'): Removed *objPath from revision store");
	} else {
		failmsg(-808000, "uuRevisionRemove: Revision_id not found or permission denied.");
	}
}

# \brief uuRevisionRestore
# \param[in] revision_id	id of revision data object
# \param[in] overwrite		1 = overwrite old path with revision, 0 = put file next to original file.
uuRevisionRestore(*revision_id, *overwrite) {
      #| writeLine("stdout", "Restore a revision");
	*isfound = false;
	foreach(*rev in SELECT DATA_NAME, COLL_NAME WHERE DATA_ID = "*revision_id") {
		if (!*isfound) {
			*isfound = true;
			*revName = *rev.DATA_NAME;
			*revCollName = *rev.COLL_NAME;
			*src =  *revCollName ++ "/" ++ *revName;
			} else {
	#| 			writeLine("stdout", "original_path is set more than once");
				fail;
		}
	}

	if (!*isfound) {
		failmsg(-1, "Could not find revision");
	}

       # Get MetaData
	msiString2KeyValPair("", *kvp);
	uuObjectMetadataKvp(*revision_id, UUORGMETADATAPREFIX, *kvp);
       # Check if original_coll_name exists
	msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_coll_name", *collName);

	if (!uuCollectionExists(*collName)) {
	 	#writeLine("serverLog", "uuRevisionRestore: (re)creating *collName");
		msiCollCreate(*collName, 1, *status);
     #| 	writeLine("stdout", "Status of msiCollCreate is *status");	
	}
	*options = "";
	if (*overwrite == 1) {
		msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_path", *dst);
		msiAddKeyValToMspStr("forceFlag", "", *options);
	} else {
		*dst = *coll_name ++ "/" ++ *revName;
	}
	msiAddKeyValToMspStr("verifyChksum", "", *options);
	*err = errorcode(msiDataObjCopy(*src, *dst, *options, *status));
}

# \brief uuRevisionLast return last revision
# \param[in] oricollid Original Collection id
# \param[in] oriobjid Original Object id
# \param[out] isfound Flag set when the last revision was found
# \param[out] revision 	dataObject of revision
uuRevisionLast(*originalPath, *isfound, *revision) {
	#| writeLine("stdout", "Return last revision of dataobject");
	msiString2KeyValPair("", *revision);
	*isfound = false;
	foreach(*row in SELECT DATA_ID, DATA_CHECKSUM, order_desc(DATA_CREATE_TIME) WHERE META_DATA_ATTR_NAME = 'org_original_path' AND META_DATA_ATTR_VALUE = *originalPath) {
		if (!*isfound) {
			*isfound = true;
			*id = *row.DATA_ID;
			*revision.id = *id;
			*revision.checksum = *row.DATA_CHECKSUM;
			*revision.timestamp = *row.DATA_CREATE_TIME;
			foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
				*name = *meta.META_DATA_ATTR_NAME;
				*val = *meta.META_DATA_ATTR_VALUE;
				msiAddKeyVal(*revision, *name, *val);
			}
		}
	}
}


# \brief uuRevisionList list revisions of path
uuRevisionList(*path, *revisions) {
	#| writeLine("stdout", "List revisions of path");
	*revisions = list();
	uuChopPath(*path, *coll_name, *data_name);
	*isFound = false;
	foreach(*row in SELECT DATA_ID, DATA_CHECKSUM, DATA_SIZE, order_asc(DATA_CREATE_TIME) WHERE META_DATA_ATTR_NAME = 'org_original_path' AND META_DATA_ATTR_VALUE = *path) {
		msiString2KeyValPair("", *kvp); # only way as far as I know to initialize a new key-value-pair object each iteration.
		*isFound = true;
		*id = *row.DATA_ID;
		*kvp.id = *id;
		*kvp.checksum = *row.DATA_CHECKSUM;
		*kvp.timestamp = *row.DATA_CREATE_TIME;
		*kvp.filesize = *row.DATA_SIZE;
		foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			msiAddKeyVal(*kvp, *name, *val);	
		}

		*revisions = cons(*kvp, *revisions);
	}
	# Step 1: Identify revisions
       	# - Query iRODS for data object in /zone/revisions/grp-of-*owner with ori- metadata set to COLL_NAME and DATA_NAME of the dataobject
	# Step 2: Create return list *revisions
	# - For each object found create a tuple with:
	#	- object id of revision
	#	- Timestamp of revision
	#	- User who added revision
	#	- file size
	#	- checksum
}

uuRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME","DATA_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME", "DATA_CHECKSUM", "DATA_SIZE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchstring), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);

	foreach(*kvp in tl(*kvpList)) {
		*id = *kvp.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *kvp);
	}

	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

uuRevisionSearchByOriginalId(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME", "DATA_CHECKSUM", "DATA_SIZE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_id"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchid), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);

	foreach(*kvp in tl(*kvpList)) {
		*id = *kvp.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *kvp);
	}
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

uuRevisionVacuum(*status) {
	writeLine("stdout", "Vacuuming revisions store");
	# Step 1: Check if store exceeds 50% of total storage available
	#  - If not, return status success
	# Step 2: Identify revisions older than 180 days in /zone/revisions
	# Step 3: For each old revision, check if newer revision is stored to ensure researcher the option to revert to the last revision
	# Step 4: If newer revisions are available remove the old revision
	# Step 5: Check if storage is below 50%
	# Step 6: If not, repeat process with 90 days treshold (and 60, then 30)
}

