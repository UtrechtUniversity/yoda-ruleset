# \file
# \brief Revision management
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#####################################################
#
# \brief uuRevisionCreate create a revision of a dataobject in a revision folder
# \param[in] path		path of data object to create a revision for
# \param[out] id		object id of revision
# \param[out] status		return failure or success
uuRevisionCreate(*path, *id, *status) {
	*status = 0
	#| writeLine("stdout", "Create a revision of a file");
	#| writeLine("stdout", "Current User: $userNameClient");
	# Step 1: Check requisites:
	# - path should return a dataObject
	uuChopPath(*path, *parent, *basename);
	msiGetIcatTime(*timestamp, "unix");
	#| writeLine("stdout", *timestamp);
	msiString2KeyValPair("", *revkv);
	msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_path", *path);
	msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_collection_name", *parent);
	msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_name", *basename);
	msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "revision_created_by_user", $userNameClient);

	*objectId = 0;
	*found = false;
	foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, USER_NAME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID, COLL_OWNER_NAME WHERE DATA_NAME = *basename AND COLL_NAME = *parent) {
		if (!*found) {
	#| 		writeLine("stdout", *row);
			*found = true;
			*objectId = *row.DATA_ID;
			*lastModified = *row.DATA_MODIFY_TIME;
			*dataSize = *row.DATA_SIZE;
			*collId = *row.COLL_ID;
			*userName = *row.USER_NAME;
			*collOwner = *row.COLL_OWNER_NAME;
			*dataOwner = *row.DATA_OWNER_NAME;
		} else {
			status = -1;
			failmsg(-1, "Multiple results for path found");
		}
	}
	if (!*found) {
		*status = -1;
		failmsg(-1, "DataObject was not found or path was collection");
	} else {
	#| 	writeLine("stdout", "Found Data object with id: *objectId modified: *lastModified");
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_user_name", *userName);
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_owner_name", *collOwner);
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_owner_name", *dataOwner);
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_id", *objectId);
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_id", *collId);
		msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "lastModified", *lastModified);
	}
	# - Parent collection is not locked or freezed

	uuLockExists(*parent, *isLocked);
	if (*isLocked) {
		failmsg(-1, "Collection *parent is Locked");
	} else {
	#| 	writeLine("stdout", "Collection *parent is not locked");
	}

	*revisionStore = "/$rodsZoneClient/revisions/*userName";
	#| writeLine("stdout", *revisionStore);
	# - Object is owned by current active group or user
	# - Object is not larger than 500MiB
	#! writeLine("stdout", "Size=*dataSize");
	if (int(*dataSize)>500048576) {
		failmsg(-1, "Files larger than 500MiB cannot store revisions");
	}	

	# Step 2: gather metadata:
	# metadata of original + new values:
	# prefix: ori-
	# - original Collection name / id
	# - original Object name / id 
	# - original owner: group / user
	# - current timestamp
	# - checksum of data

	# Step 3: create new data object:
	# Create a temporary file within in the /zone/revisions store
	# Collection is /zone/revisions/*grp
	*tmpFileName = *basename ++ "_" ++ *collId ++ "_" ++ $userNameClient ++ "_" ++ *timestamp;
	*tmpPath = *revisionStore ++ "/" ++ *tmpFileName;
	#| writeLine("stdout", *tmpFileName);
	# Copy of data
	msiDataObjChksum(*path, "forceChksum=", *checksum);
	msiDataObjCopy(*path, *tmpPath, "verifyChksum=", *status);
	# Step 4: rename object in store to object id
	foreach(*row in SELECT DATA_ID WHERE DATA_NAME = *tmpFileName AND COLL_NAME = *revisionStore) {
		*dataId = *row.DATA_ID;
	}
	*revPath = *revisionStore ++ "/" ++ *dataId;
	#! writeLine("stdout", *revPath);
	msiDataObjRename(*tmpPath, *revPath, 0, *status);
	msiAssociateKeyValuePairsToObj(*revkv, *revPath, "-d");
}


# \brief uuRevisionRestore
# \param[in] revision_id	id of revision data object
# \param[out] status		return success or failure
uuRevisionRestore(*revision_id, *status) {
	#| writeLine("stdout", "Restore a revision");
	*isfound = false;
	foreach(*rev in SELECT DATA_NAME, DATA_CHECKSUM, COLL_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = "*revision_id" AND META_DATA_ATTR_NAME = "original_path") {
		if (!*isfound) {
			*isfound = true;
			*src = *rev.COLL_NAME ++ "/" ++ *rev.DATA_NAME;
			*dst = *rev.META_DATA_ATTR_VALUE;
			*revChksum = *rev.DATA_CHECKSUM;
			} else {
	#| 			writeLine("stdout", "original_path is set more than once");
				fail;
		}
	}

	if (!*isfound) {
		failmsg(-1, "Could not find revision");
	}

	# Get MetaData
	uuObjectMetadataKvp(*revision_id, "original", *kvp);
	# Check if original_coll_name exists
	*coll_name = *kvp."original_coll_name";
	*exists = uuCollectionExists(*coll_name);
	if (*exists) {
	#| 	writeLine("stdout", "*coll_name exists");
	} else {
	#| 	writeLine("stdout", "Creating *coll_name");
		msiCollCreate(*coll_name, "1", *status);
	#| 	writeLine("stdout", "Status of msiCollCreate is *status");	
	}
	#| writeLine("stdout", "Source: *src");
	#| writeLine("stdout", "Destination: *dst");
	msiAddKeyValToMspStr("forceFlag", "", *options);
	msiAddKeyValToMspStr("verifyChksum", "", *options);
	#| writeLine("stdout", *options);
	*ec = errorcode(msiDataObjCopy(*src, *dst, *options, *status));
	#| writeLine("stdout", "restore returned errorcode: *ec");		

	# Step 1: Find revision in store
	# - Search based on id
	# - check if ori- metadata is as expected
	# Step 2: Compare checksums
	# - Should differ
	# - If it is the same then restoring the revision is unneeded
	# Step 3: Compare metadata
	# - Only different data needs to be overwritten
	# Step 4: Create revision of data object that will be overwritten
	# Step 5: Overwrite data object with data from revision if needed
	# Step 6: Overwrite metadata that differs from revision if needed
	# Step 7: Report success or failure of the operation
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
	foreach(*row in SELECT DATA_ID, DATA_CHECKSUM, order_desc(DATA_CREATE_TIME) WHERE META_DATA_ATTR_NAME = 'original_path' AND META_DATA_ATTR_VALUE = *originalPath) {
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

uuRevisionList2(*originalPath, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *originalPath), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuSearchDataObjectsTemplate(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

uuRevisionSearchByName(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"));
        *conditions = cons(makelikecondition("META_DATA_ATTR_VALUE", *searchstring), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuSearchDataObjectsTemplate(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

uuRevisionSearchById(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_id"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchid), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);

	uuSearchDataObjectsTemplate(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
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

