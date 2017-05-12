# \file
# \brief     Status transitions for Folders in the Research area.
# \author    Paul Frederiks
# \copyright Copyright (c) 2015 - 2017 Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

# \brief iiFolderStatus
# \param[in]  folder	    Path of folder
# \param[out] folderstatus  Current status of folder
iiFolderStatus(*folder, *folderstatus) {
	
	*folderstatuskey = IISTATUSATTRNAME;
	*folderstatus = FOLDER;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderstatuskey) {
		*folderstatus = *row.META_COLL_ATTR_VALUE;
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
	if (*currentStatus == FOLDER && *newStatus == LOCKED) {
		# Add locks to folder, descendants and ancestors
		iiFolderLockChange(*folder, true, *status);
	} else if (*currentStatus == LOCKED && *newStatus == FOLDER) {
		# Remove locks from folder, descendants and ancestors
		iiFolderLockChange(*folder, false, *status);
	} else if (*currentStatus == FOLDER && *newStatus == SUBMITTED) {
		# Check if the yoda-metadata.xml conforms to the XSD
		*xmlpath = *folder ++ "/" ++ IIMETADATAXMLNAME;
		*zone = hd(split(triml(*folder, "/"), "/"));
		*err = errorcode(iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath));
		if (*err < 0) { 
			if (*err == -808000) {
				failmsg(-808000, "Folder submitted without metadata");
			}
			fail(*err);
		}
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", "iiFolderTransition: *err - *msg");	
			failmsg(-1110000, "Rollback needed");
		}

		# lock the folder.
		iiFolderLockChange(*folder, true, *status);

		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == LOCKED && *newStatus == SUBMITTED) {
		*xmlpath = *folder ++ "/" ++ IIMETADATAXMLNAME;
		*zone = hd(split(triml(*folder, "/"), "/"));
		iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath);
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", "iiFolderTransition: *err - *msg");	
			failmsg(-1110000, "Rollback needed");
		}
		succeed;
	} else if (*currentStatus == SUBMITTED && *newStatus == LOCKED) {
		succeed;
	} else if (*currentStatus == SUBMITTED && *newStatus == ACCEPTED) {
		succeed;
	}
}


# \brief iiPostFolderStatusTransition   Processing after Status had changed
# \param[in] folder
# \param[in] actor
# \param[in] newStatus
iiPostFolderStatusTransition(*folder, *actor, *newStatus) {
	if (*newStatus == SUBMITTED) {
		iiAddActionLogRecord(*actor, *folder, *newStatus);
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (!*datamanagerExists) {
			msiString2KeyValPair(IISTATUSATTRNAME ++ "=" ++ ACCEPTED, *kvp);
			msiAssociateKeyValuePairsToObj(*kvp, *folder, "-C");
		}
	} else if (*newStatus == ACCEPTED) {
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (*datamanagerExists) {
			iiAddActionLogRecord(*actor, *folder, *newStatus);
		} else {
			iiAddActionLogRecord("system", *folder, *newStatus);
		}
	} else if (*newStatus == FOLDER) {
		*actionLog = UUORGMETADATAPREFIX ++ "action_log";	
		iiRemoveAVUs(*folder, *actionLog);
	} else {
		iiAddActionLogRecord(*actor, *folder, *newStatus);
	}	
}

# \brief iiFolderLock
# \param[in] path of folder to lock
iiFolderLock(*folder) {
	*status_str = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		writeLine("stdout", "iiFolderLock: Failed - *err, *msg");
	}
}

# \brief iiFolderUnlock
# \param[in] folder	path of folder to unlock
iiFolderUnlock(*folder) {
	*attrName = IISTATUSATTRNAME;
	*currentStatus = FOLDER;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *attrName) {
		*currentStatus = *row.META_COLL_ATTR_VALUE;
	}
	if (*currentStatus != FOLDER) {
		*status_str = *attrName ++ "=" ++ *currentStatus;
		msiString2KeyValPair(*status_str, *statuskvp);
		*err = errormsg(msiRemoveKeyValuePairsFromObj(*statuskvp, *folder, "-C"), *msg);	
		if (*err < 0) {
			writeLine("stdout", "iiFolderLock: Failed - *err, *msg");
		}
	}
}

# \brief iiFolderSubmit
# \param[in] folder	path of folder to submit to vault 
iiFolderSubmit(*folder) {
	*status_str = IISTATUSATTRNAME ++ "=" ++ SUBMITTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		writeLine("stdout", "iiFolderLock: Failed - *err, *msg");
	}
}

# \brief iiFolderUnsubmit
# \param[in] *folder            - path of folder to unsubmit when set saving to vault
iiFolderUnsubmit(*folder) {
	*status_str = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	
	if (*err < 0) {
		writeLine("serverLog", "iiFolderUnsubmit: Failed - (*err, *msg)");
        }
}

# \brief iiFolderAccept    accept a folder for the vault
# \param[in] folder
iiFolderAccept(*folder) {
	iiCollectionGroupName(*folder, *groupName);
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*aclKv.actor = uuClientFullName;
	msiSudoObjAclSet(0, "write", "datamanager-*category", *folder, *aclKv);
	*status_str = IISTATUSATTRNAME ++ "=" ++ ACCEPTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	msiSudoObjAclSet(0, "read", "datamanager-*category", *folder, *aclKv);
}

# \brief iiFolderReject    reject a folder for the vault
# \param[in] folder
iiFolderReject(*folder) {
	iiCollectionGroupName(*folder, *groupName);
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*aclKv.actor = uuClientFullName;
	msiSudoObjAclSet(0, "write", "datamanager-*category", *folder, *aclKv);
	*status_str = IISTATUSATTRNAME ++ "=" ++ REJECTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	msiSudoObjAclSet(0, "read", "datamanager-*category", *folder, *aclKv);
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
iiActionLog(*folder, *result) {
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

