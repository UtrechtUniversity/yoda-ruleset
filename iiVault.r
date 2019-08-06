# \file      iiVault.r
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


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


# \brief iiCopyFolderToVault
#
# \param[in] folder  folder to copy to the vault
# \param[in] target  path of the vault package
#
iiCopyFolderToVault(*folder, *target) {

	writeLine("stdout", "iiCopyFolderToVault: Copying *folder to *target")
	*buffer.source = *folder;
	*buffer.destination = *target ++ "/original";
	uuTreeWalk("forward", *folder, "iiIngestObject", *buffer, *error);
	if (*error != 0) {
		msiGetValByKey(*buffer, "msg", *msg); # using . syntax here lead to type error
		writeLine("stdout", "iiIngestObject: *error: *msg");
		fail;
	}
}

# \brief iiSetVaultPermissions
#
# \param[in] folder  folder to copy to the vault
# \param[in] target  path of the vault package
#
iiSetVaultPermissions(*folder, *target) {

	*err = errorcode(iiCollectionGroupName(*folder, *groupName));
	if (*err < 0) {
		writeLine("stdout", "iiSetVaultPermissions: Cannot determine which research group *folder belongs to");
		fail;
	} else {
		writeLine("stdout", "iiSetVaultPermissions: *folder belongs to *groupName");
	}

	uuChop(*groupName, *_, *baseName, "-", true);
        *vaultGroupName = IIVAULTPREFIX ++ *baseName;

	# Check if noinherit is set
	*inherit = "0"; # COLL_INHERITANCE can be empty which is interpreted as noinherit
	foreach(*row in SELECT COLL_INHERITANCE WHERE COLL_NAME = "/$rodsZoneClient/home/*vaultGroupName") {
		*inherit = *row.COLL_INHERITANCE;
	}

	#DEBUG writeLine("stdout", "iiSetVaultPermissions: COLL_INHERITANCE = '*inherit' on /$rodsZoneClient/home/*vaultGroupName");

	if (*inherit == "1") {
		# Setting main collection of vault group to noinherit for finegrained access control
		*err = errorcode(msiSetACL("recursive", "admin:noinherit", "", "/$rodsZoneClient/home/*vaultGroupName"));
		if (*err < 0) {
			writeLine("stdout", "iiSetVaultPermissions: Failed to set noinherit on /$rodsZoneClient/home/*vaultGroupName. errorcode: *err");
			fail;
		} else {
			writeLine("stdout", "iiSetVaultPermissions: No inherit set on /$rodsZoneClient/home/*vaultGroupName");
			# Check if research group has reas-only access
			foreach(*row in SELECT USER_ID WHERE USER_NAME = *groupName) {
				*groupId =  *row.USER_ID;
				#DEBUG writeLine("stdout", "iiSetVaultPermissions: USER_ID = *groupId WHERE USER_NAME = *groupName");
			}
			*accessName = "null";
			foreach(*row in SELECT COLL_ACCESS_NAME WHERE COLL_ACCESS_USER_ID = *groupId) {
				*accessName = *row.COLL_ACCESS_NAME;
				#DEBUG writeLine("stdout", "iiSetVaultPermissions: COLL_ACCESS_NAME = *accessName WHERE COLL_ACCESS_USER_ID = *groupId");
			}

			if (*accessName !=  "read object") {
				# Grant the research group read-only acccess to the collection to enable browsing through the vault.
				*err = errorcode(msiSetACL("default", "admin:read", *groupName, "/$rodsZoneClient/home/*vaultGroupName"));
				if (*err < 0) {
					writeLine("stdout", "iiSetVaultPermissions: Failed to grant *groupName read access to *vaultGroupName. errorcode: *err");
					fail;
				} else {
					writeLine("stdout", "iiSetVaultPermissions: Granted *groupName read access to /$rodsZoneClient/home/*vaultGroupName");
				}
			}
		}
	}

	# Check if vault group has ownership
	foreach(*row in SELECT USER_ID WHERE USER_NAME = *vaultGroupName) {
		*vaultGroupId = *row.USER_ID;
		#DEBUG writeLine("stdout", "iiSetVaultPermissions: USER_ID = *vaultGroupId WHERE USER_NAME = *vaultGroupName");
	}

	*vaultGroupAccessName = "null";
	foreach (*row in SELECT COLL_ACCESS_NAME WHERE COLL_ACCESS_USER_ID = *vaultGroupId) {
		*vaultGroupAccessName = *row.COLL_ACCESS_NAME;
		#DEBUG writeLine("stdout", "iiSetVaultPermissions: COLL_ACCESS_NAME = *vaultGroupAccessName WHERE COLL_ACCESS_USER_ID = *vaultGroupId");
	}

	# Ensure vault-groupName has ownership on vault package
	if (*vaultGroupAccessName != "own") {
		*err = msiSetACL("recursive", "admin:own", *vaultGroupName, *target);
		if (*err < 0) {
			writeLine("stdout", "iiSetVaultPermissions: Failed to set own for *vaultGroupName on *target");
		} else {
			writeLine("stdout", "iiSetVaultPermissions: Set own for *vaultGroupName on *target");
		}
	}

	# Grant datamanager group read access to vault package.
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*datamanagerGroupName = "datamanager-" ++ *category;
	uuGroupExists(*datamanagerGroupName, *datamanagerExists);
	if (*datamanagerExists) {
        	*err = errorcode(msiSetACL("recursive", "admin:read", *datamanagerGroupName, *target));
		if (*err < 0) {
			writeLine("stdout", "iiSetVaultPermissions: Failed to give *datamanagerGroupName read access. errorcode: *err");
			fail;
		} else {
			writeLine("stdout", "iiSetVaultPermissions: Granted *datamanagerGroupName read access to *target");
		}

	}

	# Grant research group read access to vault package.
	*err = errorcode(msiSetACL("recursive", "admin:read", *groupName, *target));
	if (*err < 0) {
		writeLine("stdout", "iiSetVaultPermissions: Failed to give *groupName read access. errorcode: *err");
		fail;
	} else {
		writeLine("stdout", "iiSetVaultPermissions: Granted *groupName read access to *target");
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
	    *error = errorcode(msiDataObjCopy(*sourcePath, *destPath, "verifyChksum=", *status));
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
		*error = errorcode(msiDataObjCopy(*sourcePath, *destPath, "verifyChksum=", *status));
		if (*error < 0) {
			*buffer.msg = "Failed to copy *sourcePath to *destPath";
		}
	}
}


# \brief Copy user metadata from source to destination.
#
# \param[in] source
# \param[in] destination
#
iiCopyUserMetadata(*source, *destination) {
	*userMetadataPrefix = UUUSERMETADATAPREFIX ++ "%";
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
			WHERE COLL_NAME = *source
			AND META_COLL_ATTR_NAME like *userMetadataPrefix) {
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *row.META_COLL_ATTR_NAME, *row.META_COLL_ATTR_VALUE);
		msiAssociateKeyValuePairsToObj(*kvp, *destination, "-C");
	}

}


# \brief Copy the action log from the source to destination.
#
# \param[in] source
# \param[in] destination
#
iiCopyActionLog(*source, *destination) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
	       		WHERE META_COLL_ATTR_NAME = *actionLog
		       	AND COLL_NAME = *source) {
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *row.META_COLL_ATTR_NAME, *row.META_COLL_ATTR_VALUE);
		msiAssociateKeyValuePairsToObj(*kvp, *destination, "-C");
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


# \brief When a license is added to the metadata and it is available in the License collection,
#        this will copy the text to the package in the vault.
#
# \param[in] folder  	          folder to copy to the vault
# \param[in] target               path of the vault package
#
iiCopyLicenseToVaultPackage(*folder, *target) {
	*licenseKey = UUUSERMETADATAPREFIX ++ "0_License";
	*license = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *licenseKey) {
		*license = *row.META_COLL_ATTR_VALUE;
	}

	if (*license == "") {
		writeLine("serverLog", "iiCopyLicenseToVaultPackage: No license found in user metadata");
		succeed;
	}

	*licenseText = "/" ++ $rodsZoneClient ++ IILICENSECOLLECTION ++ "/" ++ *license ++ ".txt";
	if (uuFileExists(*licenseText)) {
		*destination = *target ++ "/License.txt"
		*err = errorcode(msiDataObjCopy(*licenseText, *destination, "verifyChksum=", *status));
		if (*err < 0) {
			writeLine("serverLog", "iiCopyLicenseToVaultPackage:*err; Failed to copy *licenseText to *destination");
			succeed;
		}
	} else {
		writeLine("serverLog", "iiCopyLicenseToVaultPackage: License text not available for: *license");
	}

	*licenseUriFile = "/" ++ $rodsZoneClient ++ IILICENSECOLLECTION ++ "/" ++ *license ++ ".uri";
	if (uuFileExists(*licenseUriFile)) {
		msiDataObjOpen("objPath=*licenseUriFile", *fd);
		msiDataObjRead(*fd, 2000, *buf);
		msiDataObjClose(*fd, *status);
		msiBytesBufToStr(*buf, *licenseUri);

		# Remove qoutes from string. This prevents whitespace and linefeeds from slipping into the URI
		*licenseUri = triml(trimr(*licenseUri, '"'), '"');
		msiAddKeyVal(*licenseKvp, UUORGMETADATAPREFIX ++ "license_uri", *licenseUri);
		msiAssociateKeyValuePairsToObj(*licenseKvp, *target, "-C");
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

# \brief Make system metadata accesible conform standard to the front end.
#
# \param[in] vaultPackage Package in the vault to retrieve system metadata from
# \param[out] result
# \param[out] status
# \param[out] statusInfo
#
iiFrontEndSystemMetadata(*vaultPackage, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = *vaultPackage;
	*result = "[]";
	*size = 0;

	# Package size
        iiFileCount(*vaultPackage, *totalSize, *dircount, *filecount, *modified);
        *unit = "bytes";
        if (*totalSize > 10000) {
                *totalSize = *totalSize / 1000;
                *unit = "KB";
        }
        if (*totalSize > 10000) {
                *totalSize = *totalSize / 1000;
                *unit = "MB";
        }
        if (*totalSize > 10000) {
                *totalSize = *totalSize / 1000;
                *unit = "GB";
	}
        *totalSize = floor(*totalSize);

	# Don't count vault package.
	*dircount = int(*dircount) - 1;

	*packageSizeArr = "[]";
	msi_json_arrayops(*packageSizeArr, "Package size", "add", *size);
	msi_json_arrayops(*packageSizeArr, "*filecount files, *dircount folders, total of *totalSize *unit", "add", *size);
	msi_json_arrayops(*result, *packageSizeArr, "add", *size);


        # Modified date
	*modifiedDate = "null";
	foreach (
		# Retrieve package modified date.
	        *row in
		SELECT META_COLL_ATTR_VALUE
	        WHERE  COLL_NAME           = *vaultPackage
		AND    META_COLL_ATTR_NAME = "org_publication_lastModifiedDateTime"
	) {
		*modifiedDate = *row.META_COLL_ATTR_VALUE;
	}

	if (*modifiedDate != "null") {
	        *splitModifiedDate = split(*modifiedDate, "T");
		*date = elem(*splitModifiedDate, 0);
		*timeAndZone = elem(*splitModifiedDate, 1);

		*splitTimeAndZone = split(*timeAndZone, "+");
		*sign = "+";
		if (size(*splitTimeAndZone) < 2) {
		   *splitTimeAndZone = split(*timeAndZone, "-");
		   *sign = "-";
		}
		*time = elem(*splitTimeAndZone, 0);
		*zone = elem(*splitTimeAndZone, 1);

		*modifiedDateArr = "[]";
	        msi_json_arrayops(*modifiedDateArr, "Modified date", "add", *size);
	        msi_json_arrayops(*modifiedDateArr, "*date *time UTC*sign*zone", "add", *size);
	        msi_json_arrayops(*result, *modifiedDateArr, "add", *size);
	}

        # Landingpage URL
	*landingpageURL = "null";
	foreach (
		# Retrieve package landingpage URL.
	        *row in
	        SELECT META_COLL_ATTR_VALUE
		WHERE  COLL_NAME           = *vaultPackage
		AND    META_COLL_ATTR_NAME = "org_publication_landingPageUrl"
	) {
		*landingpageURL = *row.META_COLL_ATTR_VALUE;
	}

	if (*landingpageURL != "null") {
                *landinpageURLArr = "[]";
	        msi_json_arrayops(*landinpageURLArr, "Landingpage URL", "add", *size);
	        msi_json_arrayops(*landinpageURLArr, "<a href=\"*landingpageURL\">*landingpageURL</a>", "add", *size);
	        msi_json_arrayops(*result, *landinpageURLArr, "add", *size);
	}

        # Package DOI
	*yodaDOI = "null";
	foreach (
		# Retrieve package DOI.
	        *row in
		SELECT META_COLL_ATTR_VALUE
		WHERE  COLL_NAME           = *vaultPackage
		AND    META_COLL_ATTR_NAME = "org_publication_yodaDOI"
	) {
		*yodaDOI = *row.META_COLL_ATTR_VALUE;
	}

	if (*yodaDOI != "null") {
	        *packageDOIArr = "[]";
	        msi_json_arrayops(*packageDOIArr, "Persistent Identifier", "add", *size);
		if (*landingpageURL != "null") {
	                msi_json_arrayops(*packageDOIArr, "DOI: <a href=\"*landingpageURL\">*yodaDOI</a>", "add", *size);
		} else {
	                msi_json_arrayops(*packageDOIArr, "DOI: *yodaDOI", "add", *size);
		}
	        msi_json_arrayops(*result, *packageDOIArr, "add", *size);
	}

	# EPIC PID
	*epicPID = "null";
	foreach (
		# Retrieve package EPIC PID
	        *row in
		SELECT META_COLL_ATTR_VALUE
		WHERE  COLL_NAME           = *vaultPackage
		AND    META_COLL_ATTR_NAME = "org_epic_pid"
	) {
		*epicPID = *row.META_COLL_ATTR_VALUE;
	}

	# EPIC URL
	*epicURL = "null";
	foreach (
		# Retrieve package EPIC URL
	        *row in
		SELECT META_COLL_ATTR_VALUE
		WHERE  COLL_NAME           = *vaultPackage
		AND    META_COLL_ATTR_NAME = "org_epic_url"
	) {
		*epicURL = *row.META_COLL_ATTR_VALUE;
	}

	if (*epicPID != "null") {
		*epicPIDArr = "[]";
	        msi_json_arrayops(*epicPIDArr, "EPIC Persistent Identifier", "add", *size);
		if (*epicURL != "null") {
	                msi_json_arrayops(*epicPIDArr, "<a href=\"*epicURL\">*epicPID</a>", "add", *size);
		} else {
	                msi_json_arrayops(*epicPIDArr, "*epicPID", "add", *size);
		}
	        msi_json_arrayops(*result, *epicPIDArr, "add", *size);
	}
}

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
	*status = "SUCCESS";
	*statusInfo = "";
	delay("<PLUSET>1s</PLUSET>") {
                iiCopyFolderToResearch(*folder, *target);
        }
}

#---------------- End of Yoda Front Office API ----------------
