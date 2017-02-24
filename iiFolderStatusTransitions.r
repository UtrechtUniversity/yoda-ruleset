# \brief iiFolderStatus
iiFolderStatus(*folder, *folderstatus) {
	
	*folderstatuskey = UUORGMETADATAPREFIX ++ "status";
	*folderstatus = UNPROTECTED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderstatuskey) {
		*folderstatus = *row.META_COLL_ATTR_VALUE;
	}
	
}



# \brief iiFolderProtect

iiFolderProtect(*folder) {
	iiFolderStatus(*folder, *folderstatus);
	if (iiIsStatusTransitionLegal(*folderstatus, PROTECTED)) {
		*lockName = UUORGMETADATAPREFIX ++ "lock_protect";
		iiFolderLockChange(*folder, *lockName, true, *status);
		if (*status == 0) {
			*folderstatuskey = UUORGMETADATAPREFIX ++ "status";
			msiString2KeyValPair("*folderstatuskey=" ++ PROTECTED, *statuskvp);
			msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");			
		}
	} else {
		failmsg(-1, "Illegal status change. *folderstatus -> " ++  PROTECTED);
	}
}
# \brief iiFolderUnprotect
iiFolderUnprotect(*folder) {
	iiFolderStatus(*folder, *folderstatus);
	if (iiIsStatusTransitionLegal(*folderstatus, UNPROTECTED)) {
		*lockName = UUORGMETADATAPREFIX ++ "lock_protect";
		iiFolderLockChange(*folder, *lockName, false, *status);
		if (*status == 0) {
			*folderstatuskey = UUORGMETADATAPREFIX ++ "status";
			msiString2KeyValPair("*folderstatuskey=" ++ PROTECTED, *statuskvp);
			msiRemoveKeyValuePairsFromObj(*statuskvp, *folder, "-C");			
		}
	} else {
		failmsg(-1, "Illegal status change. *folderstatus -> " ++ UNPROTECTED);
	}
}


# \brief iiFolderLockChange
# \param[in] rootCollection 	The COLL_NAME of the collection the dataset resides in
# \param[in] lockName			Key name of the meta data object that is added
# \param[in] lockIt 			Boolean, true if the object should be locked.
# 									if false, the lock is removed (if allowed)
# \param[out] status 			Zero if no errors, non-zero otherwise
iiFolderLockChange(*rootCollection, *lockName, *lockIt, *status){
	if (*lockIt) {
		msiGetIcatTime(*timestamp, "unix");
		msiString2KeyValPair("*lockName=*timestamp", *kvp)
		writeLine("serverLog", "iiFolderLockChange: recursive locking of *rootCollection");
		*direction = "forward";
		uuTreeWalk(*direction, *rootCollection, "iiSetMetadataOnItem", *kvp, *error);
		*status = *error;
	} else {
		*direction="reverse";
		*kvp.key = *lockName;
		uuTreeWalk(*direction, *rootCollection, "iiRemoveMetadataKeyOnItem", *kvp, *error);	
		*status = *error;
	}
}

iitypeabbreviation(*itemIsCollection) =  if *itemIsCollection then "-C" else "-d"

#                                itemParent  = full iRODS path to the parent of this object
#                                  itemName  = basename of collection or dataobject
#                                  itemIsCollection = true if the item is a collection
#                                  buffer = in/out Key-Value variable
#                                       the buffer is maintained by treewalk and passed
#                                       on to the processing rule. can be used by the rule
#                                       to communicate data to subsequent rule invocations
#                                       buffer."error" can be updated by the rule to indicate
#                                       an error, the treewalk will stop

iiSetMetadataOnItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiSetMetadataOnItem: Setting *buffer on *objPath");
	*error = errorcode(msiSetKeyValuePairsToObj(*buffer, *objPath, *objType));
}

iiRemoveMetadataKeyOnItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiRemoveMetadataOnItem: Removing *buffer on *objPath");
	*key = *buffer.key;
	if (*itemIsCollection) {
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *key AND COLL_NAME = *objPath) {
			*val = *row.META_COLL_ATTR_VALUE;
			*error = errorcode(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType));
			if (*error == -819000) { *error = 0 }
		}
	} else {
		uuChopPath(*objPath, *coll, *basename);
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *key AND COLL_NAME = *coll AND DATA_NAME = *basename) {
			*val = *row.META_DATA_ATTR_VALUE;
			*error = errorcode(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType));
			if (*error == -819000) { *error = 0 }
		}
	}
}
