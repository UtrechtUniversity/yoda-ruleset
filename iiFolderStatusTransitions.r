# \file      iiFolderStatusTransitions.r
# \brief     Status transitions for folders in the research space.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# ---------------- Start of Yoda FrontOffice API ----------------

# \brief Wrapper for iiActionLog to make it accessible conform standard to the front office.
#
# \param[in]  folder     folder name to be extended with required full qualification name
# \param[out] result
# \param[out] status
# \param[out] statusInfo
#
iiFrontEndActionLog(*folder, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = *folder;

	iiActionLog(*folder, *size, *result);
}

#---------------- End of Yoda Front Office API ----------------


# \brief iiFolderStatus
#
# \param[in]  folder	    Path of folder
# \param[out] folderStatus  Current status of folder
#
iiFolderStatus(*folder, *folderStatus) {
	*folderStatusKey = IISTATUSATTRNAME;
	*folderStatus = FOLDER;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderStatusKey) {
		*folderStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief Check if a datamanager group exists for the category that the group of a folder belongs to.
#
# \param[in]  folder
# \param[out] datamananagerExists
#
iiFolderDatamanagerExists(*folder, *datamanagerExists) {
	iiCollectionGroupName(*folder, *groupName);
	uuGroupGetCategory(*groupName, *category, *subcategory);
	uuGroupExists("datamanager-*category", *datamanagerExists);
}

# \brief Actions taken before status transition.
#
# \param[in] folder            Path of folder
# \param[in] currentStatus     Current status of folder
# \param[in] newStatus         New status of folder
#
iiPreFolderStatusTransition(*folder, *currentFolderStatus, *newFolderStatus) {
	on (*currentFolderStatus != LOCKED &&
	    (*newFolderStatus == LOCKED || *newFolderStatus == SUBMITTED)) {
	        # Clear action log coming from SECURED state.
	        # SECURED -> LOCKED and SECURED -> SUBMITTED
	        if (*currentFolderStatus == SECURED) {
                        *actionLog = UUORGMETADATAPREFIX ++ "action_log";
                        iiRemoveAVUs(*folder, *actionLog);
	        }

		# Add locks to folder, descendants and ancestors
		iiFolderLockChange(*folder, true, *status);
		if (*status != 0) { fail; }
	}
	on (*newFolderStatus == FOLDER || *newFolderStatus == REJECTED ||
	    *newFolderStatus == SECURED) {
	        # Clear action log coming from SECURED state.
	        # SECURED -> FOLDER (backwards compatibility for v1.2 and older)
	        if (*currentFolderStatus == SECURED) {
                        *actionLog = UUORGMETADATAPREFIX ++ "action_log";
                        iiRemoveAVUs(*folder, *actionLog);
	        }

		# Remove locks from folder, descendants and ancestors
		iiFolderLockChange(*folder, false, *status);
		if (*status != 0) { fail; }
	}
	on (true) {
		nop;
	}

}

# \brief Processing after status had changed.
#
# \param[in] folder
# \param[in] actor
# \param[in] newStatus
#
iiPostFolderStatusTransition(*folder, *actor, *newFolderStatus) {
	on (*newFolderStatus == SUBMITTED) {
		iiAddActionLogRecord(*actor, *folder, "submitted for vault");
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (!*datamanagerExists) {
			msiString2KeyValPair(IISTATUSATTRNAME ++ "=" ++ ACCEPTED, *kvp);
			msiSetKeyValuePairsToObj(*kvp, *folder, "-C");
		}
	}
	on (*newFolderStatus == ACCEPTED) {
		iiFolderDatamanagerExists(*folder, *datamanagerExists);
		if (*datamanagerExists) {
			iiAddActionLogRecord(*actor, *folder, "accepted for vault");
		} else {
			iiAddActionLogRecord("system", *folder, "accepted for vault");
		}

		# Set cronjob state.
		msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_PENDING, *kvp);
		msiSetKeyValuePairsToObj(*kvp, *folder, "-C");
		iiScheduleCopyToVault();
	}
	on (*newFolderStatus == FOLDER) {
		iiActionLog(*folder, *size, *actionLog);
		if (*size > 0) {
			*log = "";
			msi_json_arrayops(*actionLog, *log, "get", *size - 1);
			msi_json_arrayops(*log, *log, "get", 1);
			if (*log == "submitted for vault") {
				iiAddActionLogRecord(*actor, *folder, "unsubmitted for vault");
				succeed;
			}
		}
		iiAddActionLogRecord(*actor, *folder, "unlocked");
	}
	on (*newFolderStatus == LOCKED) {
		iiAddActionLogRecord(*actor, *folder, "locked");
	}
	on (*newFolderStatus == REJECTED) {
		iiAddActionLogRecord(*actor, *folder, "rejected for vault");
	}
	on (*newFolderStatus == SECURED) {
		iiAddActionLogRecord("system", *folder, "secured in vault");
	}
	on (true) {
		nop;
	}
}

# \brief Schedule copy-to-vault (asynchronously).
#
iiScheduleCopyToVault() {
	delay ("<PLUSET>1s</PLUSET>") {
		msiExecCmd("scheduled-copytovault.sh", "", "", "", 0, *out);
	}
}

# \brief Lock a folder in the research space.
#
# \param[in]  folder        path of folder to lock
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderLock(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiFolderStatus(*folder, *currentFolderStatus);
	if (*currentFolderStatus != FOLDER && *currentFolderStatus != REJECTED && *currentFolderStatus != SECURED) {
		*status = "WrongStatus";
		*statusInfo = "Cannot lock folder as it is currently in *currentFolderStatus state";
		succeed;
	}
	*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ LOCKED;
	msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentFolderStatus);
		*actor = uuClientFullName;
                iiCanTransitionFolderStatus(*folder, *currentFolderStatus, LOCKED, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
		}
	} else {
		*status = "Success";
		*statusInfo = "";
	}
}

# \brief Unlock a folder in the research space.
#
# \param[in]  folder        path of folder to unlock
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderUnlock(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiFolderStatus(*folder, *currentFolderStatus);
	if (*currentFolderStatus == LOCKED || *currentFolderStatus == SUBMITTED || *currentFolderStatus == REJECTED || *currentFolderStatus == SECURED) {
		*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ *currentFolderStatus;
		msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
		*err = errormsg(msiRemoveKeyValuePairsFromObj(*folderStatusKvp, *folder, "-C"), *msg);
	} else {
		*status = "WrongStatus";
		if (*currentFolderStatus == FOLDER) {
			*statusInfo = "Insufficient permissions or the folder is  currently not in a locked state.";
		} else {
			*statusInfo = "Cannot unlock folder as it is currently in *currentFolderStatus state.";
		}
		succeed;
	}
	if (*err < 0) {
		*actor = uuClientFullName;
		iiCanTransitionFolderStatus(*folder, *currentFolderStatus, FOLDER, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
		}
	} else {
		*status = "Success";
		*statusInfo = "";
	}
}

# \brief iiFolderSubmit
#
# \param[in]  folder	    path of folder to submit to vault
# \param[out] folderStatus  status of the folder after submission
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderSubmit(*folder, *folderStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiFolderStatus(*folder, *currentFolderStatus);
	if (*currentFolderStatus == FOLDER || *currentFolderStatus == SECURED ||
	    *currentFolderStatus == REJECTED || *currentFolderStatus == LOCKED) {
		*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ SUBMITTED;
		msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
		*err = errormsg(msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C"), *msg);
	} else {
		*status = "WrongStatus";
		*statusInfo = "Cannot unlock folder as it is currently in *currentFolderStatus state";
		*folderStatus = *currentFolderStatus;
		succeed;
	}
	if (*err < 0) {
		iiCanTransitionFolderStatus(*folder, *currentFolderStatus, SUBMITTED, uuClientFullName, *allowed, *reason);
		if (!*allowed) {
		      *status = "PermissionDenied";
		      *statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
	 	}
	} else {
		*status = "Success";
		*statusInfo = "";
		iiFolderStatus(*folder, *folderStatus);
	}
}

# \brief Unsubmit a folder submitted to the vault.
#
# \param[in]  folder        path of folder to unsubmit when set saving to vault
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderUnsubmit(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiFolderStatus(*folder, *currentFolderStatus);
	if (*currentFolderStatus == SUBMITTED) {
		*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ *currentFolderStatus;
		msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
		*err = errormsg(msiRemoveKeyValuePairsFromObj(*folderStatusKvp, *folder, "-C"), *msg);
	} else {
		*status = "WrongStatus";
		*statusInfo = "Folder cannot be unsubmitted because its state has changed.";
		succeed;
	}
	if (*err < 0) {
		iiCanTransitionFolderStatus(*folder, *currentFolderStatus, FOLDER, uuClientFullName, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
		}
        } else {
		*status = "Success";
		*statusInfo = "";
	}
}

# \brief iiFolderDatamanagerAction
#
# \param[in] folder
# \param[out] newFolderStatus Status to set as datamanager. Either ACCEPTED or REJECTED
# \param[out] status          status of the action
# \param[out] statusInfo      Informative message when action was not successfull
#
iiFolderDatamanagerAction(*folder, *newFolderStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	# Check if folder is a research group.
	*err = errorcode(iiCollectionGroupName(*folder, *groupName));
	if (*err < 0) {
		*status = "NoResearchGroup";
		*statusInfo = "*folder is not accessible possibly due to insufficient rights or as it is not part of a research group. Therefore, the requested action can not be performed";
		succeed;
	} else {
		# Research group, determine datamanager group.
		uuGroupGetCategory(*groupName, *category, *subcategory);
               *datamanagerGroup = "datamanager-*category";
	}

	*actor = uuClientFullName;
	*aclKv.actor = *actor;
	*err = errorcode(msiSudoObjAclSet("recursive", "write", *datamanagerGroup, *folder, *aclKv));
	if (*err < 0) {
		*status = "PermissionDenied";
		iiCanDatamanagerAclSet(*folder, *actor, *datamanagerGroup, 0, "write", *allowed, *reason);
		if (*allowed) {
			*statusInfo = "Could not acquire datamanager access to *folder.";
		} else {
			*statusInfo = *reason;
		}
		succeed;
	}
	if (*newFolderStatus == REJECTED) {
		# get permission to unlock ancestors, too
		uuChopPath(*folder, *parent, *child);
		while(*parent != "/$rodsZoneClient/home") {
			msiSudoObjAclSet("", "write", *datamanagerGroup, *parent, *aclKv);
			uuChopPath(*parent, *coll, *child);
			*parent = *coll;
		}
	}
	*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ *newFolderStatus;
	msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiFolderStatus(*folder, *currentFolderStatus);
		iiCanTransitionFolderStatus(*folder, *currentFolderStatus, *newFolderStatus, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
		}
	}
	*err = errormsg(msiSudoObjAclSet("recursive", "read", *datamanagerGroup, *folder, *aclKv), *msg);
	if (*err < 0) {
		*status = "FailedToRemoveTemporaryAccess";
		iiCanDatamanagerAclSet(*folder, *actor, *datamanagerGroup, 0, "read", *allowed, *reason);
		if (*allowed) {
			*statusInfo = "*err - *msg";
		} else {
			*statusInfo = *reason;
		}
		succeed;
	}
	if (*newFolderStatus == REJECTED) {
		# remove permission to modify ancestors
		uuChopPath(*folder, *parent, *child);
		while(*parent != "/$rodsZoneClient/home") {
			msiSudoObjAclSet("", "read", *datamanagerGroup, *parent, *aclKv);
			uuChopPath(*parent, *coll, *child);
			*parent = *coll;
		}
	}
	if (*status == "Unknown") {
		*status = "Success";
		*statusInfo = "";
	}
}

# \brief Accept a folder for the vault.
#
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderAccept(*folder, *status, *statusInfo) {
	iiFolderDatamanagerAction(*folder, ACCEPTED, *status, *statusInfo);
}

# \brief Reject a folder for the vault.
#
# \param[in] folder
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
#
iiFolderReject(*folder, *status, *statusInfo) {
	iiFolderDatamanagerAction(*folder, REJECTED, *status, *statusInfo);
}

# \brief iiFolderSecure   Secure a folder to the vault. This function should only be called by a rodsadmin
#			  and should not be called from the portal. Thus no statusInfo is returned, but
#			  log messages are sent to stdout instead
#
# \param[in] folder
#
iiFolderSecure(*folder) {
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		writeLine("stdout", "iiFolderSecure: Should only be called by a rodsadmin");
		fail;
	}

	# Check modify access on research folder.
	msiCheckAccess(*folder, "modify object", *modifyAccess);

	# Set cronjob status.
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_PROCESSING, *kvp);
	if (*modifyAccess != 1) {
		msiSetACL("default", "admin:write", uuClientFullName, *folder);
	}
	msiSetKeyValuePairsToObj(*kvp, *folder, "-C");
	*found = false;
	foreach (*row in SELECT META_COLL_ATTR_VALUE
			 WHERE COLL_NAME = '*folder'
			 AND META_COLL_ATTR_NAME = IICOPYPARAMSNAME) {
		# retry with previous parameters
		*target = *row.META_COLL_ATTR_VALUE;
		*found = true;
	}
	if (*found) {
		# Remove parameters from metadata
		msiString2KeyValPair("", *kvp);
		*key = IICOPYPARAMSNAME;
		*kvp."*key" = *target;
		msiRemoveKeyValuePairsFromObj(*kvp, *folder, "-C");
	}
	if (*modifyAccess != 1) {
		msiSetACL("default", "admin:null", uuClientFullName, *folder);
	}

	if (!*found) {
		*target = iiDetermineVaultTarget(*folder);
	}

	# Try to register EPIC PID
	iiRegisterEpicPID(*target, *url, *pid, *httpCode);
	if (*httpCode != "0" && *httpCode != "200" && *httpCode != "201") {
		# Always retry
		writeLine("serverLog", "iiFolderSecure: msiRegisterEpicPID returned *httpCode");
		msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_RETRY, *kvp);
		*key = IICOPYPARAMSNAME;
		*kvp."*key" = *target;
		if (*modifyAccess != 1) {
			msiSetACL("default", "admin:write", uuClientFullName, *folder);
		}
		msiSetKeyValuePairsToObj(*kvp, *folder, "-C");
		if (*modifyAccess != 1) {
			msiSetACL("default", "admin:null", uuClientFullName, *folder);
		}
		fail;
	}

	# Copy to vault
	iiCopyFolderToVault(*folder, *target);
	iiCopyUserMetadata(*folder, *target);
	iiCopyOriginalMetadataToVault(*target);
	iiCopyLicenseToVaultPackage(*folder, *target);

	if (*httpCode != "0") {
		# save EPIC Persistent ID in metadata
		iiSaveEpicPID(*target, *url, *pid);
	}

	# Set research folder status.
	*folderStatusStr = IISTATUSATTRNAME ++ "=" ++ SECURED;
	msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
	msiSetACL("recursive", "admin:write", uuClientFullName, *folder);
	uuChopPath(*folder, *parent, *child);
	while(*parent != "/$rodsZoneClient/home") {
		msiSetACL("default", "admin:write", uuClientFullName, *parent);
		uuChopPath(*parent, *coll, *child);
		*parent = *coll;
	}
	msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C");
	msiSetACL("recursive", "admin:null", uuClientFullName, *folder);
	uuChopPath(*folder, *parent, *child);
	while(*parent != "/$rodsZoneClient/home") {
		msiSetACL("default", "admin:null", uuClientFullName, *parent);
		uuChopPath(*parent, *coll, *child);
		*parent = *coll;
	}

	# Copy and write provenance log.
	iiCopyActionLog(*folder, *target);
	iiWriteProvenanceLogToVault(*target);

	# Set vault permissions for new vault package.
	iiSetVaultPermissions(*folder, *target);

	# Set vault package status.
	*vaultStatus = IIVAULTSTATUSATTRNAME;
	msiString2KeyValPair("*vaultStatus=" ++ UNPUBLISHED, *vaultStatusKvp);
	msiSetKeyValuePairsToObj(*vaultStatusKvp, *target, "-C");

	# Set cronjob status.
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_OK, *kvp);
	if (*modifyAccess != 1) {
		msiSetACL("default", "admin:write", uuClientFullName, *folder);
	}
	msiSetKeyValuePairsToObj(*kvp, *folder, "-C");
	if (*modifyAccess != 1) {
		msiSetACL("default", "admin:null", uuClientFullName, *folder);
	}
}

# \brief iiRegisterEpicPID create and try to register an EPIC PID
#
# \param[in]  target
# \param[out] url
# \param[out] pid
# \param[out] httpCode
#
iiRegisterEpicPID(*target, *url, *pid, *httpCode) {
	# Get URL
	iiGetPublicationConfig(*config);
	*host = *config.davrodsVHost;
	*subpath = triml(*target, "/home/");
	*url = "https://*host/*subpath";

	# Generate new EPIC PID
	msiGenerateUUID(*pid);

	# Try to register EPIC PID
	*httpCode = "-1";
	errorcode(msiRegisterEpicPID(*url, *pid, *httpCode));
}

# \brief iiSaveEpicPID save persistent EPIC ID
#
# \param[in]  target
# \param[out] url
# \param[out] pid
#
iiSaveEpicPID(*target, *url, *pid) {
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "epic_pid=" ++ *pid, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *target, "-C");
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "epic_url=" ++ *url, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *target, "-C");
}

# \brief iiAddActionLogRecord
#
# \param[in] actor
# \param[in] folder
# \param[in] action
#
iiAddActionLogRecord(*actor, *folder, *action) {
	msiGetIcatTime(*timestamp, "icat");
	writeLine("serverLog", "iiAddActionLogRecord: *actor has *action *folder");
        *json_str = "[]";
        *size = 0;
        msi_json_arrayops(*json_str, *timestamp, "add", *size);
        msi_json_arrayops(*json_str, *action, "add", *size);
        msi_json_arrayops(*json_str, *actor, "add", *size);
	msiString2KeyValPair("", *kvp);
	msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "action_log", *json_str);
	*status = errorcode(msiAssociateKeyValuePairsToObj(*kvp, *folder, "-C"));
}

# \brief iiActionLog
#
# \param[in]  folder
# \param[out] size
# \param[out] result
#
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
#
# \param[in] rootCollection 	The COLL_NAME of the collection the dataset resides in
# \param[in] lockIt 		Boolean, true if the object should be locked.
#				if false, the lock is removed (if allowed)
# \param[out] status 		Zero if no errors, non-zero otherwise
#
iiFolderLockChange(*rootCollection, *lockIt, *status){
	msiString2KeyValPair("", *buffer);
	msiAddKeyVal(*buffer, IILOCKATTRNAME, *rootCollection)
	#DEBUG writeLine("ServerLog", "iiFolderLockChange: *buffer");
	if (*lockIt) {
		#DEBUG writeLine("serverLog", "iiFolderLockChange: recursive locking of *rootCollection");
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
		#DEBUG writeLine("serverLog", "iiFolderLockChange: recursive unlocking of *rootCollection");
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

# \brief Return objectType string based on boolean itemIsCollection.
#
# \param[in] itemIsCollection	boolean usually returned by treewalk when item is a Collection
# \returnvalue		        iRODS objectType string. "-C" for Collection, "-d" for DataObject
#
iitypeabbreviation(*itemIsCollection) =  if *itemIsCollection then "-C" else "-d"

# \brief For use by uuTreewalk to add metadata.
#
# \param[in] itemParent            full iRODS path to the parent of this object
# \param[in] itemName              basename of collection or dataobject
# \param[in] itemIsCollection      true if the item is a collection
# \param[in,out] buffer            in/out Key-Value variable
# \param[out] error                errorcode in case of failure
#
iiAddMetadataToItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	#DEBUG writeLine("serverLog", "iiAddMetadataToItem: Setting *buffer on *objPath");
	*error = errorcode(msiAssociateKeyValuePairsToObj(*buffer, *objPath, *objType));
}

# \brief For use by uuTreeWalk to remove metadata.
#
# \param[in] itemParent            full iRODS path to the parent of this object
# \param[in] itemName              basename of collection or dataobject
# \param[in] itemIsCollection      true if the item is a collection
# \param[in,out] buffer            in/out Key-Value variable
# \param[out] error                errorcode in case of failure
#
iiRemoveMetadataFromItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	#DEBUG writeLine("serverLog", "iiRemoveMetadataKeyFromItem: Removing *buffer on *objPath");
	*error = errormsg(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType), *msg);
	if (*error < 0) {
		writeLine("serverLog", "iiRemoveMetadataFromItem: removing *buffer from *objPath failed with errorcode: *error");
		writeLine("serverLog", *msg);
		if (*error == -819000) {
			# This happens when metadata was already removed or never there.
			writeLine("serverLog", "iiRemoveMetadaFromItem: -819000 detected. Keep on trucking, this happens if metadata was already removed");
			*error = 0;
		}
	}
}
