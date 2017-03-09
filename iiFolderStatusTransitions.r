# \brief iiFolderStatus
iiFolderStatus(*folder, *folderstatus) {
	
	*folderstatuskey = UUORGMETADATAPREFIX ++ "status";
	*folderstatus = UNPROTECTED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderstatuskey) {
		*folderstatus = *row.META_COLL_ATTR_VALUE;
	}
}

iiFolderTransition(*path, *currentStatus, *newStatus) {
	if (*currentStatus == UNPROTECTED && *newStatus == PROTECTED) {
		iiFolderLockChange(*path, "protect", true, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == PROTECTED && (*newStatus == UNPROTECTED || *newStatus == "")) {
		iiFolderLockChange(*path, "protect", false, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == UNPROTECTED && *newStatus == SUBMITTED) {
		# protect the folder.
		iiFolderLockChange(*path, "protect", true, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == PROTECTED && *newStatus == SUBMITTED) {
		# nothing to do
		succeed;
	}
}

# \brief iiFolderProtect
# \param[in] folder	path of folder to protect
iiFolderProtect(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ PROTECTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");
}

# \brief iiFolderUnprotect
# \param[in] folder	path of folder to protect
iiFolderUnprotect(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ UNPROTECTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");	
}

# \brief iiFolderSubmit
# \param[in] folder	path of folder to submit to vault 
iiFolderSubmit(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ SUBMITTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");
}

# \brief iiFolderLockChange
# \param[in] rootCollection 	The COLL_NAME of the collection the dataset resides in
# \param[in] lockName			Key name of the meta data object that is added
# \param[in] lockIt 			Boolean, true if the object should be locked.
# 									if false, the lock is removed (if allowed)
# \param[out] status 			Zero if no errors, non-zero otherwise
iiFolderLockChange(*rootCollection, *lockName, *lockIt, *status){
	*lock_str = UUORGMETADATAPREFIX ++ "lock_" ++ *lockName ++ "=" ++ *rootCollection;
	writeLine("ServerLog", "iiFolderLockChange: *lock_str");
	msiString2KeyValPair(*lock_str, *buffer)

	if (*lockIt) {
		writeLine("serverLog", "iiFolderLockChange: recursive locking of *rootCollection");
		*direction = "forward";
		uuTreeWalk(*direction, *rootCollection, "iiAddMetadataToItem", *buffer, *error);
		if (*error == 0) {
			uuChopPath(*rootCollection, *parent, *child);
			while(*parent != "/$rodsZoneClient/home") {
				uuChopPath(*parent, *coll, *child);
				iiAddMetadataToItem(*coll, *child, true, *buffer, *error); 
			 	*parent = *coll;
			}
		}
	} else {
		writeLine("serverLog", "iiFolderLockChange: recursive unlocking of *rootCollection");
		*direction="reverse";
		uuTreeWalk(*direction, *rootCollection, "iiRemoveMetadataFromItem", *buffer, *error);	
		if (*error == 0) {
			uuChopPath(*rootCollection, *parent, *child);
			while(*parent != "/$rodsZoneClient/home") {
				uuChopPath(*parent, *coll, *child);
				iiRemoveMetadataFromItem(*coll, *child, true, *buffer, *error); 
			 	*parent = *coll;
			}
		}

	}

	*status = *error;
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

iiAddMetadataToItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiAddMetadataToItem: Setting *buffer on *objPath");
	*error = errorcode(msiAssociateKeyValuePairsToObj(*buffer, *objPath, *objType));
}

iiRemoveMetadataFromItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiRemoveMetadataKeyFromItem: Removing *buffer on *objPath");
	*error = errormsg(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType), *msg);
	if (*error < 0) {
		writeLine("serverLog", "iiRemoveMetadataFromItem: removing *buffer from *objPath failed with errorcode: *error");
		writeLine("serverLog", *msg);
		if (*error == -819000) {
			writeLine("serverLog", "iiRemoveMetadaFromItem: -819000 detected. Keep on trucking");
			*error = 0;
		}
	}
}
