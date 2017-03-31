# \file
# \brief     Revision management
# \author    Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license   GPLv3, see LICENSE
#
#####################################################
#

# \brief uuResourceModifiedPostRevision 	Create revisions on file modifications
# \description				This policy should trigger whenever a new file is added or modified
#					in the workspace of a Research team. This should be done asynchronously
# \param[in,out] out	This is a required argument for Dynamic PEP's in the 4.1.x releases. It is unused.
uuResourceModifiedPostRevision(*pluginInstanceName, *KVPairs) {
	if (*KVPairs.logical_path like "/" ++ *KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "*") {
		writeLine("serverLog", "uuResourceModifiedPostRevision:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		*path = *KVPairs.logical_path;
		uuChopPath(*path, *parent, *basename);
		if (*basename like "._*") {
			# MacOS writes to ._ multiple times per put
			writeLine("serverLog", "uuResourceModifiedPostRevision: Ignore *basename for revision store. This is littering by Mac OS");
		} else {
			iiRevisionCreateAsynchronously(*path);
		}
	}
}

# \brief uuRevisionCreateAsynchronously  Asynchronous call to uuRevisionCreate
# \param[in] path	The path of the added or modified file.
iiRevisionCreateAsynchronously(*path) {
	remote("localhost", "") {
		delay("<PLUSET>1s</PLUSET>") {
			iiRevisionCreate(*path, *id);
			writeLine("serverLog", "uuRevisionCreate: Revision created for *path ID=*id");
		}
	}
}

# \brief iiRevisionCreate create a revision of a dataobject in a revision folder
# \param[in] path		path of data object to create a revision for
# \param[out] id		object id of revision
iiRevisionCreate(*path, *id) {
	#| writeLine("stdout", "Create a revision of a file");
	#| writeLine("stdout", "Current User: $userNameClient");
	# Step 1: Check requisites:
	# - path should return a dataObject
	*id = "";
	uuChopPath(*path, *parent, *basename);
       #| writeLine("stdout", *timestamp);
	*objectId = 0;
	*found = false;
	foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID
	       		WHERE DATA_NAME = *basename AND COLL_NAME = *parent AND DATA_REPL_NUM = "0") {
		if (!*found) {
       #| 		writeLine("stdout", *row);
			*found = true;
			*dataId = *row.DATA_ID;
			*modifyTime = *row.DATA_MODIFY_TIME;
			*dataSize = *row.DATA_SIZE;
			*collId = *row.COLL_ID;
			*dataOwner = *row.DATA_OWNER_NAME;
		}
	}

	if (!*found) {
		writeLine("serverLog", "iiRevisionCreate: DataObject was not found or path was collection");
		succeed;
	}


	if (int(*dataSize)>500048576) {
		writeLine("serverLog", "iiRevisionCreate: Files larger than 500MiB cannot store revisions");
		succeed;
	}	


	foreach(*row in SELECT USER_NAME, USER_ZONE WHERE DATA_ID = *dataId AND USER_TYPE = "rodsgroup" AND DATA_ACCESS_NAME = "own") {
	       *groupName = *row.USER_NAME;
		*userZone = *row.USER_ZONE;
	}

	*revisionStore = "/*userZone" ++ UUREVISIONCOLLECTION ++ "/*groupName";

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
				writeLine("serverLog", "iiRevisionCreate: *revPath already exists. This means that *basename was changed multiple times within the same second.");
			} else if (*err == -814000) {
			# -814000 CAT_UNKNOWN_COLLECTION
				writeLine("serverLog", "iiRevisionCreate: Could not access or create *revColl. Please check permissions");
			} else {
				failmsg(*err, "iiRevisionCreate failed");
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
		writeLine("serverLog", "iiRevisionCreate: *revisionStore does not exists or is inaccessible for current client.");
	}
}


# \brief iiRevisionRemove
# \param[in] revision_id
iiRevisionRemove(*revision_id) {
	*isfound = false;
	*revisionStore =  "/$rodsZoneClient" ++ UUREVISIONCOLLECTION;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revision_id" AND COLL_NAME like "*revisionStore/%") {
		if (!*isfound) {
			*isfound = true;
			*objPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		} else {
			writeLine("serverLog", "iiRevisionRemove: *revision_id returned multiple results");
		}
	}
	if (*isfound) {
		*args = "";
		msiAddKeyValToMspStr("objPath", *objPath, *args);
		msiAddKeyValToMspStr("forceFlag", "", *args);
		msiDataObjUnlink(*args, *status);
		writeLine("serverLog", "iiRevisionRemove('*revision_id'): Removed *objPath from revision store");
	} else {
		writeLine("serverLog", "iiRevisionRemove: Revision_id not found or permission denied.");
	}
}

# \brief iiRevisionRestore
# \param[in] revision_id	id of revision data object
# \param[in] target		target collection to write in
# \param[in] overwrite		yes = overwrite old path with revision, no = put file next to original file.
# \param[out] status		status of restore process
iiRevisionRestore(*revisionId, *target, *overwrite, *status) {
      #| writeLine("stdout", "Restore a revision");
	*status = "Unknown error";
	*isfound = false;
	foreach(*rev in SELECT DATA_NAME, COLL_NAME WHERE DATA_ID = *revisionId) {
		if (!*isfound) {
			*isfound = true;
			*revName = *rev.DATA_NAME;
			*revCollName = *rev.COLL_NAME;
			*src = *revCollName ++ "/" ++ *revName;
		}
	}

	if (!*isfound) {
		*status = "Could not find revision *revisionId"
		writeLine("serverLog", "iiRevisionRestore: *status");
		succeed;
	}

       # Get MetaData
	msiString2KeyValPair("", *kvp);
	uuObjectMetadataKvp(*revisionId, UUORGMETADATAPREFIX, *kvp);

	if (!uuCollectionExists(*target)) {
		*status = "Cannot find *target";
		writeLine("serverLog", "iiRevisionRestore: *status");
		succeed;
	}

	if (*overwrite == "yes") {
		msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);
		msiAddKeyValToMspStr("forceFlag", "", *options);
		*dst = *target ++ "/" ++ *oriDataName;
	} else {
		*dst = *target ++ "/" ++ *revName;
	}
	msiAddKeyValToMspStr("verifyChksum", "", *options);
	writeLine("serverLog", "iiRevisionRestore: *src => *dst [*options]");
	*err = errormsg(msiDataObjCopy("*src", "*dst", *options, *msistatus), *errmsg);
	if (*err < 0) {
		*status = "Restoration failed with error *err: *errmsg"
		writeLine("serverLog", "iiRevisionRestore: *status");
	} else {
		*status = "Success";
	}
}

# \brief iiRevisionLast return last revision
# \param[in] oricollid Original Collection id
# \param[in] oriobjid Original Object id
# \param[out] isfound Flag set when the last revision was found
# \param[out] revision 	dataObject of revision
iiRevisionLast(*originalPath, *isfound, *revision) {
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


# \brief iiRevisionList list revisions of path
# \param[in]  path     Path of original file
# \param[out] result   List in JSON format with all revisions of the original path
iiRevisionList(*path, *result) {
	#| writeLine("stdout", "List revisions of path");
	*revisions = list();
	uuChopPath(*path, *coll_name, *data_name);
	*isFound = false;
	foreach(*row in SELECT DATA_ID, DATA_CHECKSUM, DATA_SIZE, order_desc(DATA_CREATE_TIME) 
		        WHERE META_DATA_ATTR_NAME = 'org_original_path' AND META_DATA_ATTR_VALUE = *path) {
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
	
	uuKvpList2JSON(*revisions, *result, *size);	
}

# \brief iiRevisionSearchByOriginalPath 
# TODO: Refactor to support sorting and searching on filename instead of complete path
iiRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("META_DATA_ATTR_VALUE", "COUNT(DATA_ID)");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"),
			   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*res.originalPath = *kvp.META_DATA_ATTR_VALUE;
		*res.numberOfRevisions = *kvp.DATA_ID;
		*result_lst = cons(*res, *result_lst);
	}
	
	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}

# \brief iiRevisionSearchByOriginalFilename
# TODO: See iiRevisionSearchByOriginalPath
iiRevisionSearchByOriginalFilename(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("META_DATA_ATTR_VALUE", "COUNT(DATA_ID)");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_data_name"),
        		   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));	
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*res.originalPath = *kvp.META_DATA_ATTR_VALUE;
		*res.numberOfRevisions = *kvp.DATA_ID;
		*result_lst = cons(*res, *result_lst);
	}
	
	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}

# \brief iiRevisionSearchByOriginalId
# Id stays the same after file renames.
iiRevisionSearchByOriginalId(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
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

	*kvpList = cons(hd(*kvpList), uuListReverse(tl(*kvpList)));
	
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

