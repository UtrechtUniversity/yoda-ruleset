# \file      iiFolderStatusTransitions.r
# \brief     Status transitions for folders in the research space.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

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

# \brief Schedule copy-to-vault (asynchronously).
#
iiScheduleCopyToVault() {
	delay ("<PLUSET>1s</PLUSET>") {
		msiExecCmd("scheduled-copytovault.sh", "", "", "", 0, *out);
	}
}


# \brief iiFolderDatamanagerAction
#
# \param[in] folder
# \param[out] newFolderStatus Status to set as datamanager. Either ACCEPTED or REJECTED
# \param[out] status          status of the action
# \param[out] statusInfo      Informative message when action was not successful
#
iiFolderDatamanagerAction(*folder, *newFolderStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	# Check if folder is a research group.
	*groupName = "";
	*err = errorcode(rule_collection_group_name(*folder, *groupName));
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
	if (*lockIt == "lock") {
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

	*status = "*error";
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
                # this file
		*target = iiDetermineVaultTarget(*folder);
	}

	# Copy to vault
	iiCopyFolderToVault(*folder, *target);

        # From HERE relay to python
        *return = "";
        rule_folder_secure(*folder, *target, *return);
}


# \brief iiDetermineVaultTarget
#
# \param[in] folder
# \returnvalue target path
#
iiDetermineVaultTarget(*folder) {
	*err = errorcode(iiCollectionGroupName(*folder, *groupName));
	if (*err < 0) {
		writeLine("stdout", "iiDetermineVaultTarget: Cannot determine which research group *folder belongs to");
		fail;
	} else {
		writeLine("stdout", "iiDetermineVaultTarget: *folder belongs to *groupName");
	}
	uuChop(*groupName, *_, *baseName, "-", true);
	uuChopPath(*folder, *parent, *datapackageName);

	# Make room for the timestamp and sequence number
	if (strlen(*datapackageName) > 235) {
		*datapackageName = substr(*datapackageName, 0, 235);
	}

	msiGetIcatTime(*timestamp, "unix");
	*timestamp = triml(*timestamp, "0");
        *vaultGroupName = IIVAULTPREFIX ++ *baseName;

	*target = "/$rodsZoneClient/home/*vaultGroupName/*datapackageName[*timestamp]";

	*i = 0;
	while (uuCollectionExists(*target)) {
		writeLine("stdout", "iiDetermineVaultTarget: *target already exists");
		*i = *i + 1;
		*target = "/$rodsZoneClient/home/*vaultGroupName/*datapackageName[*timestamp][*i]";
	}
	writeLine("stdout", "iiDetermineVaultTarget: Target is *target");
	*target;
}


# \brief Return the name of the group a collection belongs to.
#
# \param[in]  path
# \param[out] groupName
#
iiCollectionGroupName(*path, *groupName) {
	*isfound = false;
	*groupName = "";
	foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
		*id = *accessid.COLL_ACCESS_USER_ID;
		foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id) {
				*groupName = *group.USER_GROUP_NAME;
		}
		if (*groupName like regex "(deposit|research|intake)-.*") {
			*isfound = true;
			break;
		}
	}

	if (!*isfound) {
		foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
			*id = *accessid.COLL_ACCESS_USER_ID;
			foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id) {
					*groupName = *group.USER_GROUP_NAME;
			}
			if (*groupName like regex "(datamanager|vault)-.*") {
				*isfound = true;
				break;
			}
		}
	}
	if (!*isfound){
		# No results found. Not a group folder
		writeLine("serverLog", "*path does not belong to a deposit, research or intake group or is not available to current user");
	}
}
