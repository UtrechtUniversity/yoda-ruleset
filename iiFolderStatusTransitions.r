# \file
# \brief     Status transitions for Folders in the Research area.
# \author    Paul Frederiks
# \copyright Copyright (c) 2015 - 2017 Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE


#  FRONT END FUNCTIONS TO BE CALLED FROM PHP WRAPPER

# /brief iiFrontEndUnsubmitFolder
# /param[in]  *folder           -folder to be 'unsubmitted'
# /param[out] *data             -return actuual requested data if applicable
# /param[out] *status           -return status to frontend
# /param[out] *statusInfo       -return specific information regarding *status

iiFrontEndFolderUnsubmit(*path, *data, *status, *statusInfo)
{
        *status = UUFRONTEND_SUCCESS;
        *statusInfo = 'All went well!';

        iiFolderUnsubmit(*path, *error, *statusInfo);

        if (*error!=0) { # to be differentiated
                *status = UUFRONTEND_UNRECOVERABLE;
        }
        writeLine('serverLog', *status);
        writeLine('serverLog', *statusInfo);
}


#----------------------------------------------- END OF FRONTEND FUNCTIONS-----------------

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

# \brief iiFolderTransition    Dispatch rules based on status transition
# \param[in] path              Path of folder
# \param[in] currentStatus     Current status of folder
# \param[in] newStatus         New status of folder
iiFolderTransition(*path, *currentStatus, *newStatus) {
	if (*currentStatus == FOLDER && *newStatus == LOCKED) {
		iiFolderLockChange(*path, true, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		} else {
			iiAddActionLogRecord(*path, "lock");
		}
	} else if (*currentStatus == LOCKED && *newStatus == FOLDER) {
		iiFolderLockChange(*path, false, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		} else {
			*actionLog = UUORGMETADATAPREFIX ++ "action_log";	
			iiRemoveAVUs(*path, *actionLog);
		}
	} else if (*currentStatus == FOLDER && *newStatus == SUBMITTED) {
		*xmlpath = *path ++ "/" ++ IIMETADATAXMLNAME;
		*zone = hd(split(triml(*path, "/"), "/"));
		iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath);
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", "iiFolderTransition: *err - *msg");	
			failmsg(-11110000, "Rollback needed");
		}

		# lock the folder.
		iiFolderLockChange(*path, true, *status);

		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		} else {
			iiAddActionLogRecord(*path, "submit");
		}
	} else if (*currentStatus == LOCKED && *newStatus == SUBMITTED) {
		*xmlpath = *path ++ "/" ++ IIMETADATAXMLNAME;
		*zone = hd(split(triml(*path, "/"), "/"));
		iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath);
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", "iiFolderTransition: *err - *msg");	
			failmsg(-11110000, "Rollback needed");
		}
		iiAddActionLogRecord(*path, "submit");
		succeed;
	} else if (*currentStatus == SUBMITTED && *newStatus == LOCKED) {
		iiAddActionLogRecord(*path, "unsubmit");
		succeed;
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
# \param[in] folder	path of folder to submit to vault 


# \brief iiFolderUnsubmit
# \param[in] *folder            - path of folder to unsubmit when set saving to vault
# \param[out] *status           - Internal status code
# \param[out] *statusInfo       - Explanatory info when something is wrong for frontend
iiFolderUnsubmit(*folder, *status, *statusInfo) {

	# iiFolderUnsubmit(*folder) {

	*status = 0;
	*statusInfo = '';

	*status_str = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*status_str, *statuskvp);

	*err = errormsg(msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C"), *msg);
	if (*err < 0) {
		writeLine("stdout", "iiFolderLock: Failed");
                *status = -1;
                *statusInfo = 'Something went wrong while removing submitted status. (*err)';
        }
}

# \brief iiAddActionLogRecord
iiAddActionLogRecord(*folder, *action) {
	msiGetIcatTime(*timestamp, "icat");
	*actor = uuClientFullName;
	writeLine("serverLog", "iiAddActionLogRecord: *actor has peformed *action action on *folder");
	*json_str = "[\"*timestamp\", \"*action\", \"*actor\"]";
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "action_log=" ++ *json_str, *kvp);
	msiAssociateKeyValuePairsToObj(*kvp, *folder, "-C");
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

