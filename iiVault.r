# \file      iiVault.r
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2020, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief iiCopyFolderToVault
#
# \param[in] folder  folder to copy to the vault
# \param[in] target  path of the vault package
#
iiCopyFolderToVault(*folder, *target) {

	writeLine("serverLog", "iiCopyFolderToVault: Copying *folder to *target")
	*buffer.source = *folder;
	*buffer.destination = *target ++ "/original";
	uuTreeWalk("forward", *folder, "iiIngestObject", *buffer, *error);
	if (*error != 0) {
		msiGetValByKey(*buffer, "msg", *msg); # using . syntax here lead to type error
		writeLine("stdout", "iiIngestObject: *error: *msg");
		fail;
	}
}


# \brief Called by uuTreeWalk for each collection and dataobject to copy to the vault.
#
# \param[in] itemParent
# \param[in] itemName
# \param[in] itemIsCollection
# \param[in/out] buffer
# \param[in/out] error
#
iiIngestObject(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
        writeLine("serverLog", "INGEST OBJECT");
	*sourcePath = "*itemParent/*itemName";
	msiCheckAccess(*sourcePath, "read object", *readAccess);
	if (*readAccess != 1) {
		*error = errorcode(msiSetACL("default", "admin:read", uuClientFullName, *sourcePath));
		if (*error < 0) {
			*buffer.msg = "Failed to acquire read access to *sourcePath";
			succeed;
		} else {
			writeLine("stdout", "iiIngestObject: Read access to *sourcePath acquired");
		}
	}

	*destPath = *buffer.destination;
	if (*sourcePath != *buffer."source") {
		# rewrite path to copy objects that are located underneath the toplevel collection
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
		*markIncomplete = false;
	} else {
		*markIncomplete = true;
	}

	if (*itemIsCollection) {
		*error = errorcode(msiCollCreate(*destPath, 1, *status));
		if (*error < 0) {
			*buffer.msg = "Failed to create collection *destPath";
		} else if (*markIncomplete) {
			# The root collection of the vault package is marked incomplete until the last step in FolderSecure
			*vaultStatus = IIVAULTSTATUSATTRNAME;
			msiString2KeyValPair("*vaultStatus=" ++ INCOMPLETE, *kvp);
			msiAssociateKeyValuePairsToObj(*kvp, *destPath, "-C");
		}
	} else {
	    # Copy data object to vault and compute checksum.
	    *resource = "";
	    *err = errorcode(rule_resource_vault(*resource));
	    *error = errorcode(msiDataObjCopy(*sourcePath, *destPath, "destRescName=" ++ *resource ++ "++++verifyChksum=", *status));
	    if (*error < 0) {
		    *buffer.msg = "Failed to copy *sourcePath to *destPath";
	    }
	}
	if (*readAccess != 1) {
		*error = errorcode(msiSetACL("default", "admin:null", uuClientFullName, *sourcePath));
		if (*error < 0) {
			*buffer.msg = "Failed to revoke read access to *sourcePath";
		} else {
			writeLine("stdout", "iiIngestObject: Read access to *sourcePath revoked");
		}
	}
}


# \brief Called by uuTreeWalk for each collection and dataobject to copy to the research area.
#
# \param[in] itemParent
# \param[in] itemName
# \param[in] itemIsCollection
# \param[in/out] buffer
# \param[in/out] error
#
iiCopyObject(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*sourcePath = "*itemParent/*itemName";
	*destPath = *buffer.destination;

	if (*sourcePath != *buffer."source") {
		# rewrite path to copy objects that are located underneath the toplevel collection
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
	}

	if (*itemIsCollection) {
		*error = errorcode(msiCollCreate(*destPath, 1, *status));
		if (*error < 0) {
			*buffer.msg = "Failed to create collection *destPath";
		}
	} else {
		*resource = "";
		*err = errorcode(rule_resource_research(*resource));
		*error = errorcode(msiDataObjCopy(*sourcePath, *destPath, "destRescName=" ++ *resource ++ "++++verifyChksum=", *status));
		if (*error < 0) {
			*buffer.msg = "Failed to copy *sourcePath to *destPath";
		}
	}
}


#\ Generic secure copy functionality
# \param[in] argv         argument string for secure copy like "*publicHost inbox /var/www/landingpages/*publicPath";
# \param[in] origin_path  local path of origin file
# \param[out] err         return the error to calling function
#
iiGenericSecureCopy(*argv, *origin_path, *err) {
        *err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *origin_path, 1, *cmdExecOut));
        if (*err < 0) {
                msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
                msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
                writeLine("serverLog", "iiGenericSecureCopy: errorcode *err");
                writeLine("serverLog", *stderr);
                writeLine("serverLog", *stdout);
        }
}

# \brief Rule to grant read access to the vault package managed by a datamanger.
#
# \param[in] path
# \param[out] status
# \param[out] statusInfo
#
iiGrantReadAccessToResearchGroup(*path, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error occured";

	# Vault packages start four directories deep
	*pathElems = split(*path, "/");
	if (size(*pathElems) != 4) {
		*status = "PermissionDenied";
		*statusInfo = "The datamanager can only grant permissions to vault packages";
		succeed;
	}
	*vaultGroupName = elem(*pathElems, 2);
	*baseGroupName = triml(*vaultGroupName, IIVAULTPREFIX);
	*researchGroup = IIGROUPPREFIX ++ *baseGroupName;
	*actor = uuClientFullName;
	*aclKv.actor = *actor;
	*err = errormsg(msiSudoObjAclSet("recursive", "read", *researchGroup, *path, *aclKv), *msg);
	if (*err < 0) {
		*status = "PermissionDenied";
		iiCanDatamanagerAclSet(*path, *actor, *researchGroup, 1, "read", *allowed, *reason);
		if (*allowed) {
			*statusInfo = "Could not acquire datamanager access to *path.";
			writeLine("serverLog", "iiGrantReadAccessToResearchGroup: *err - *msg");
		} else {
			*statusInfo = *reason;
		}
		succeed;
	} else {
		*status = "Success";
		*statusInfo = "";
		succeed;
	}

}

# \brief Rule to revoke read access to the vault package managed by a datamanger.
#
# \param[in] path
# \param[out] status
# \param[out] statusInfo
#
iiRevokeReadAccessToResearchGroup(*path, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error occured";

	*pathElems = split(*path, "/");
	if (size(*pathElems) != 4) {
		*status = "PermissionDenied";
		*statusInfo = "The datamanager can only revoke permissions to vault packages";
		succeed;
	}
	*vaultGroupName = elem(*pathElems, 2);
	*baseGroupName = triml(*vaultGroupName, IIVAULTPREFIX);
	*researchGroup = IIGROUPPREFIX ++ *baseGroupName;
	*actor = uuClientFullName;
	*aclKv.actor = *actor;
	*err = errormsg(msiSudoObjAclSet("recursive", "null", *researchGroup, *path, *aclKv), *msg);
	if (*err < 0) {
		*status = "PermissionDenied";
		iiCanDatamanagerAclSet(*path, *actor, *researchGroup, 1, "null", *allowed, *reason);
		if (*allowed) {
			*statusInfo = "Could not acquire datamanager access to *path.";
			writeLine("serverLog", "iiGrantReadAccessToResearchGroup: *err - *msg");
		} else {
			*statusInfo = *reason;
		}
		succeed;
	} else {
			*status = "Success";
			*statusInfo = "";
			succeed;
	}
}

# \brief When inheritance is missing we need to copy ACL's when introducing new data in vault package.
#
# \param[in] path 		path of object that needs the permissions of parent
# \param[in] recursiveFlag 	either "default" for no recursion or "recursive"
#
iiCopyACLsFromParent(*path, *recursiveFlag) {
        uuChopPath(*path, *parent, *child);

        foreach(*row in SELECT COLL_ACCESS_NAME, COLL_ACCESS_USER_ID WHERE COLL_NAME = *parent) {
                *accessName = *row.COLL_ACCESS_NAME;
                *userId = *row.COLL_ACCESS_USER_ID;
                *userFound = false;

                foreach(*user in SELECT USER_NAME WHERE USER_ID = *userId) {
                        *userName = *user.USER_NAME;
                        *userFound = true;
                }

                if (*userFound) {
                        if (*accessName == "own") {
                                writeLine("serverLog", "iiCopyACLsFromParent: granting own to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "own", *userName, *path);
                        } else if (*accessName == "read object") {
                                writeLine("serverLog", "iiCopyACLsFromParent: granting read to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "read", *userName, *path);
                        } else if (*accessName == "modify object") {
                                writeLine("serverLog", "iiCopyACLsFromParent: granting write to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "write", *userName, *path);
                        }
                }
        }
}


# \brief Copy a vault package to the research area.
#
# \param[in] folder  folder to copy from the vault
# \param[in] target  path of the research area target
#
iiCopyFolderToResearch(*folder, *target) {
        writeLine("stdout", "iiCopyFolderToResearch: Copying *folder to *target.");

        # Determine target collection group and actor.
        *pathElems = split(*folder, "/");
        *elemSize = size(*pathElems);
        *vaultPackage = elem(*pathElems, *elemSize - 1);

        *buffer.source = *folder;
        *buffer.destination = *target ++ "/" ++ *vaultPackage;
        uuTreeWalk("forward", *folder, "iiCopyObject", *buffer, *error);
        if (*error != 0) {
                msiGetValByKey(*buffer, "msg", *msg); # using . syntax here lead to type error
                writeLine("stdout", "iiCopyObject: *error: *msg");
                fail;
        }
}


# ---------------- Start of Yoda FrontOffice API ----------------

# \brief Request a copy action of a vault package to the research area.
#
# \param[in] folder  	          folder to copy from the vault
# \param[in] target               path of the research area target
iiFrontRequestCopyVaultPackage(*folder, *target, *status, *statusInfo) {
	# Check if target is a research folder.
	if (*target like regex "/[^/]+/home/research-.*") {
	} else {
                *status = 'ErrorTargetPermissions';
                *statusInfo = 'Please select a folder in the research area.';
                succeed;
	}

        # Check whether datapackage folder already present in target folder.
        uuChopPath(*folder, *parent, *datapackageName);
        *newTargetCollection = "*target/*datapackageName";
        if (uuCollectionExists(*newTargetCollection)) {
                *status = 'ErrorCollectionAlreadyExists';
                *statusInfo = 'Please select another location for this datapackage as it is present already in folder you selected.';
                succeed;
        }

        # Check origin circumstances.
        iiCollectionDetails(*folder, *kvpCollDetails, *stat, *statInfo);
        if (*stat == 'ErrorPathNotExists') {
                *status = 'FO-ErrorVaultCollectionDoesNotExist';
                *statusInfo = 'The datapackage does not exist.';
                succeed;
        }

	# Check if user has read access to vault package.
        if (*kvpCollDetails.researchGroupAccess != "yes") {
                *status = 'ErrorTargetPermissions';
                *statusInfo = 'You have insufficient permissions to copy the datapackage.';
                succeed;
        }

        # Check target circumstances
        iiCollectionDetails(*target, *kvpCollDetails, *stat, *statInfo);
        if (*kvpCollDetails.lockCount != "0") {
                *status = 'FO-ErrorTargetLocked';
                *statusInfo = 'The selected folder is locked. Please unlock this folder first.';
                succeed;
        }

        # Check if user has write acces to research folder
        if (*kvpCollDetails.userType != "normal" && *kvpCollDetails.userType != "manager") {
                *status = 'ErrorTargetPermissions';
                *statusInfo = 'You have insufficient permissions to copy the datapackage to this folder. Please select another folder.';
                succeed;
        }

	# Add copy action to delayed rule queue.
	*status = "Success";
	*statusInfo = "";
	delay("<PLUSET>1s</PLUSET>") {
                iiCopyFolderToResearch(*folder, *target);
        }
}

#---------------- End of Yoda Front Office API ----------------
