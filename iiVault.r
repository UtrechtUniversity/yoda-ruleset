# \file      iiVault.r
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2022, Utrecht University. All rights reserved.
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
	*sourcePath = "*itemParent/*itemName";
	msiCheckAccess(*sourcePath, "read_object", *readAccess);
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
                        } else if (*accessName == "read_object") {
                                writeLine("serverLog", "iiCopyACLsFromParent: granting read to <*userName> on <*path> with recursiveFlag <*recursiveFlag>");
                                msiSetACL(*recursiveFlag, "read", *userName, *path);
                        } else if (*accessName == "modify_object") {
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

# \brief Retrieve current vault folder status
#
# \param[in]  folder	    Path of vault folder
# \param[out] folderStatus  Current status of vault folder
#
iiVaultStatus(*folder, *vaultStatus) {
	*vaultStatusKey = IIVAULTSTATUSATTRNAME;
	*vaultStatus = UNPUBLISHED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *vaultStatusKey) {
		*vaultStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief Retrieve actor of action on vault folder
#
# \param[in]  folder      Path of action vault folder
# \param[out] actionActor Actor of action on vault folder
#
iiVaultGetActionActor(*folder, *actor, *actionActor) {
	# Retrieve vault folder collection id.
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
	        *collId = *row.COLL_ID;
	}

        # Retrieve vault folder action actor.
        *actionActor = "";
        foreach(*row in SELECT ORDER_DESC(META_COLL_MODIFY_TIME), COLL_ID, META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = "org_vault_action_*collId") {
                *err = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actionActor, "get", 2));
                if (*err < 0) {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId contains invalid JSON");
                } else {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId actor is *actionActor");
                }
                break;
        }

        # Fallback actor (rodsadmin).
        if (*actionActor == "") {
                *actionActor = *actor;
        }
}

# \brief Perform admin operations on the vault
#
iiAdminVaultActions() {
	msiExecCmd("admin-vaultactions.sh", uuClientFullName, "", "", 0, *out);
}

# \brief Enable indexing on vault target.
iiEnableIndexing(*target) {
    msiExecCmd("enable-indexing.sh", *target, "", "", 0, *out);
}
