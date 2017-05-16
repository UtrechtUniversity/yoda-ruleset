# \file
# \brief     Status transitions for Folders in the Research area.
# \author    Paul Frederiks
# \copyright Copyright (c) 2015 - 2017 Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

# \brief iiFolderStatus
# \param[in]  folder	    Path of folder
# \param[out] folderstatus  Current status of folder
iiFolderStatus(*folder, *folderStatus) {
	
	*folderStatusKey = IISTATUSATTRNAME;
	*folderStatus = FOLDER;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderStatusKey) {
		*folderStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief iiFolderDatamanagerExists    Check if a datamanager group exists for the category that the group of a folder belongs to
# \param[in] folder
# \param[out] datamananagerExists
iiFolderDatamanagerExists(*folder, *datamanagerExists) {
	iiCollectionGroupName(*folder, *groupName);
	uuGroupGetCategory(*groupName, *category, *subcategory);
	uuGroupExists("datamanager-*category", *datamanagerExists);
}

# \brief iiPreFolderStatusTransition  Actions taken before status transition    
# \param[in] folder              Path of folder
# \param[in] currentStatus     Current status of folder
# \param[in] newStatus         New status of folder
iiPreFolderStatusTransition(*folder, *currentStatus, *newStatus) {
	on (*currentStatus == FOLDER && *newStatus == LOCKED) {
		# Add locks to folder, descendants and ancestors
		iiFolderLockChange(*folder, true, *status);
		if (*status != 0) { fail; }
	}
	on ((*currentStatus == LOCKED || *currentStatus == REJECTED || *currentStatus == SECURED) && *newStatus == FOLDER) {
		# Remove locks from folder, descendants and ancestors
		iiFolderLockChange(*folder, false, *status);
		if (*status != 0) { fail; }
	}
	on (*currentStatus == FOLDER && *newStatus == SUBMITTED) {
		iiFolderLockChange(*folder, true, *status);
		if (*status != 0) { fail; }
	}
	on (true) { 
		nop;
	}

}


# \brief iiPostFolderStatusTransition   Processing after Status had changed
# \param[in] folder
# \param[in] actor
# \param[in] newStatus
iiPostFolderStatusTransition(*folder, *actor, *newStatus) {
	on (*newStatus == SUBMITTED) {
		iiAddActionLogRecord(*actor, *folder, "submit");
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (!*datamanagerExists) {
			msiString2KeyValPair(IISTATUSATTRNAME ++ "=" ++ ACCEPTED, *kvp);
			msiAssociateKeyValuePairsToObj(*kvp, *folder, "-C");
		}
	}
	on (*newStatus == ACCEPTED) {
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (*datamanagerExists) {
			iiAddActionLogRecord(*actor, *folder, "accept");
		} else {
			iiAddActionLogRecord("system", *folder, "accept");
		}
	}
	on (*newStatus == FOLDER) {
		*actionLog = UUORGMETADATAPREFIX ++ "action_log";	
		iiRemoveAVUs(*folder, *actionLog);
	}
	on (*newStatus == LOCKED) {
		iiActionLog(*folder, *size, *actionLog);
		if (*size > 0) {
			iiAddActionLogRecord(*actor, *folder, "unsubmit");
		} else {
			iiAddActionLogRecord(*actor, *folder, "lock");
		}
	}
	on (*newStatus == REJECTED) {
		iiAddActionLogRecord(*actor, *folder, "reject");
	}
	on (*newStatus == SECURED) {
		iiAddActionLogRecord(*actor, *folder, "secured");
	}
	on (true) {
		nop;
	}
}

# \brief iiFolderLock
# \param[in] path of folder to lock
iiFolderLock(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	*status_str = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentStatus);
		*actor = uuClientFullName;
                iiCanModifyFolderStatus(*folder, *currentStatus, LOCKED, *actor, *allowed, *reason); 
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			*status = "Unrecoverable";
			*statusInfo = "*err - *msg";
		}
	} else {
		*status = "Success";
	}
}

# \brief iiFolderUnlock
# \param[in] folder	path of folder to unlock
iiFolderUnlock(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	iiFolderStatus(*folder, *currentStatus);
	*status_str = IISTATUSATTRNAME ++ "=" ++ *currentStatus;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiRemoveKeyValuePairsFromObj(*statuskvp, *folder, "-C"), *msg);	
	if (*err < 0) {
		*actor = uuClientFullName;
		iiCanModifyFolderStatus(*folder, *currentStatus, FOLDER, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			*status = "Unrecoverable";
			*statusInfo = "*err - *msg";
		}
	} else {
		*status = "Success";
		}
}

# \brief iiFolderSubmit
# \param[in] folder	path of folder to submit to vault 
iiFolderSubmit(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	*status_str = IISTATUSATTRNAME ++ "=" ++ SUBMITTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentStatus);
		iiCanModifyFolderStatus(*folder, *currentStatus, SUBMITTED, uuClientFullName, *allowed, *reason);
		if (!*allowed) {
		      *status = "PermissionDenied";
		      *statusInfo = *reason; 
		} else {
			*status = "Unrecoverable";
			*statusInfo = "*err - *msg";
	 	}		
	} else {
		*status = "Success";
	}		
}

# \brief iiFolderUnsubmit
# \param[in] *folder            - path of folder to unsubmit when set saving to vault
iiFolderUnsubmit(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	*status_str = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentStatus);
		iiCanModifyFolderStatus(*folder, *currentStatus, LOCKED, uuClientFullName, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			*status = "Unrecoverable";
			*statusInfo = "*err - *msg";
		}
        } else {
		*status = "Success";
	}
}

# \brief iiFolderDatamanagerAction    
# \param[in] folder
iiFolderDatamanagerAction(*folder, *newStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	*err = errorcode(iiCollectionGroupName(*folder, *groupName));
	if (*err < 0) {
		*status = "NoResearchGroup";
		*statusInfo = "Failed to determine research group name of *folder";
		succeed;
	}
	*actor = uuClientFullName;
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*aclKv.actor = *actor;
	*err = errorcode(msiSudoObjAclSet(0, "write", "datamanager-*category", *folder, *aclKv));
	if (*err < 0) {
		*status = "PermissionDenied";
		*statusInfo = "Could not acquire write access to *folder.";
		succeed;
	}
	*status_str = IISTATUSATTRNAME ++ "=" ++ *newStatus;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentStatus);
		iiCanModifyFolderStatus(*folder, *currentStatus, *newStatus, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = "Reason";
		} else {
			*status = "Unrecoverable";
			*statusInfo = "*err - *msg";
		}
	}
	*err = errormsg(msiSudoObjAclSet(0, "read", "datamanager-*category", *folder, *aclKv), *msg);
	if (*err < 0) {
		*status = "FailedToRemoveTemporaryAccess";
		*statusInfo = "*err - *msg"
	} else if (*status == "Unknown") {
		*status = "Success";
	}
}

iiFolderAccept(*folder, *status, *statusInfo) {
	iiFolderDatamanagerAction(*folder, ACCEPTED, *status, *statusInfo);
}

# \brief iiFolderReject    accept a folder for the vault
# \param[in] folder
iiFolderReject(*folder, *status, *statusInfo) {
	iiFolderDatamanagerAction(*folder, REJECT, *status, *statusInfo);
}

iiFolderSecure(*folder) {
	*status = "Unknown";
	*statusInfo = "";
	*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ SECURED;
	msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
	msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C");
}


# \brief iiAddActionLogRecord
iiAddActionLogRecord(*actor, *folder, *action) {
	msiGetIcatTime(*timestamp, "icat");
	writeLine("serverLog", "iiAddActionLogRecord: *actor has *action *folder");
	*json_str = "[\"*timestamp\", \"*action\", \"*actor\"]";
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "action_log=" ++ *json_str, *kvp);
	*status = errorcode(msiAssociateKeyValuePairsToObj(*kvp, *folder, "-C"));
}

# \brief iiActionLog
iiActionLog(*folder, *size, *result) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";	
	*result = "[]";
	*size = 0;
	foreach(*row in SELECT order(META_COLL_ATTR_VALUE) WHERE META_COLL_ATTR_NAME = *actionLog AND COLL_NAME = *folder) {
		*logRecord = *row.META_COLL_ATTR_VALUE;
		msi_json_arrayops(*result, *logRecord, "add", *size);
	}
}

# \brief iiFolderLockChange
# \param[in] rootCollection 	The COLL_NAME of the collection the dataset resides in
# \param[in] lockIt 			Boolean, true if the object should be locked.
# 									if false, the lock is removed (if allowed)
# \param[out] status 			Zero if no errors, non-zero otherwise
iiFolderLockChange(*rootCollection, *lockIt, *status){
	*lock_str = IILOCKATTRNAME ++ "=" ++ *rootCollection;
	msiString2KeyValPair(*lock_str, *buffer);
	writeLine("ServerLog", "iiFolderLockChange: *lock_str");
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

# \brief iiAddMetadataToItem        For use by uuTreewalk to add metadata
# \param[in] itemParent            full iRODS path to the parent of this object
# \param[in] itemName              basename of collection or dataobject
# \param[in] itemIsCollection      true if the item is a collection
# \param[in,out] buffer            in/out Key-Value variable
# \param[out] error                errorcode in case of failure
iiAddMetadataToItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiAddMetadataToItem: Setting *buffer on *objPath");
	*error = errorcode(msiAssociateKeyValuePairsToObj(*buffer, *objPath, *objType));
}

# \brief iiRemoveMetadataFromItem  For use by uuTreeWalk to remove metadata
# \param[in] itemParent            full iRODS path to the parent of this object
# \param[in] itemName              basename of collection or dataobject
# \param[in] itemIsCollection      true if the item is a collection
# \param[in,out] buffer            in/out Key-Value variable
# \param[out] error                errorcode in case of failure
iiRemoveMetadataFromItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiRemoveMetadataKeyFromItem: Removing *buffer on *objPath");
	*error = errormsg(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType), *msg);
	if (*error < 0) {
		writeLine("serverLog", "iiRemoveMetadataFromItem: removing *buffer from *objPath failed with errorcode: *error");
		writeLine("serverLog", *msg);
		if (*error == -819000) {
			# This happens when metadata was already removed or never there.
			writeLine("serverLog", "iiRemoveMetadaFromItem: -819000 detected. Keep on trucking");
			*error = 0;
		}
	}
}

