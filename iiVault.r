# \file iiVault.r
# \brief Copy folders to the vault
#
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief iiDetermineVaultTarget
# \param[in] folder
# \returnvalue target path
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
# \param[in] folder  folder to copy to the vault
# \param[in] target  path of the vault package
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
# \param[in] folder  folder to copy to the vault
# \param[in] target  path of the vault package
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
	
	# Setting main collection of vault group to noinherit for finegrained access control
	*err = errorcode(msiSetACL("recursive", "admin:noinherit", "", "/$rodsZoneClient/home/*vaultGroupName"));
	if (*err < 0) {
		writeLine("stdout", "iiSetVaultPermissions: Failed to set noinherit on /$rodsZoneClient/home/*vaultGroupName. errorcode: *err");
		fail;
	} else {
		writeLine("stdout", "iiSetVaultPermissions: No inherit set on /$rodsZoneClient/home/*vaultGroupName"); 
		# Grant the research group read-only acccess to the collection to enable browsing through the vault.
		*err = errorcode(msiSetACL("default", "admin:read", *groupName, "/$rodsZoneClient/home/*vaultGroupName"));
		if (*err < 0) {
			writeLine("stdout", "iiSetVaultPermissions: Failed to grant *groupName read access to *vaultGroupName. errorcode: *err");
			fail;
		} else {
			writeLine("stdout", "iiSetVaultPermissions: Granted *groupName read access to /$rodsZoneClient/home/*vaultGroupName");
		}
	}

	# Ensure vault-groupName has ownership on vault package
	*err = msiSetACL("recursive", "admin:own", *vaultGroupName, *target); 
	if (*err < 0) {
		writeLine("stdout", "iiSetVaultPermissions: Failed to set own on *target");
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

# \brief iiIngestObject       called by uuTreeWalk for each collection and dataobject to copy to the vault.
# \param[in] itemParent
# \param[in] itemName
# \param[in] itemIsCollection
# \param[in/out] buffer
# \param[in/out] error
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
#		*error = errorcode(msiDataObjChksum(*sourcePath, "ChksumAll=++++forceChksum=", *chksum));
#		if (*error < 0) {
#			*buffer.msg = "Failed to Checksum *sourcePath";
#		} else {
#			writeLine("stdout", "iiIngestObject: *sourcePath has checksum *chksum");
			*error = errorcode(msiDataObjCopy(*sourcePath, *destPath, "verifyChksum=", *status));
			if (*error < 0) {
				*buffer.msg = "Failed to copy *sourcePath to *destPath";
			}
#		}
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


# \brief iiCopyUserMetadata    Copy user metadata from source to destination
# \param[in] source
# \param[in] destination
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


# \brief iiCopyActionLog   Copy the action log from the source to destination
# \param[in] source
# \param[in] destination
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

# \brief iiCopyOriginalMetadataToVault    Copy the original metadata xml into the root of the package
# \param[in] vaultPackage  path of a new package in the vault
iiCopyOriginalMetadataToVault(*vaultPackage) {
	*originalMetadataXml = "*vaultPackage/original/" ++ IIMETADATAXMLNAME;
	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	msiGetIcatTime(*timestamp, "unix");
	*timestamp = triml(*timestamp, "0");
	*vaultMetadataTarget = "*vaultPackage/*baseName[*timestamp].*extension";
	msiDataObjCopy(*originalMetadataXml, *vaultMetadataTarget, "verifyChksum=", *status);
}

# \brief iiGrantReadAccessToResearchGroup Rule to grant read access to the vault package managed by a datamanger
# \param[in] path
# \param[out] status
# \param[out] statusInfo
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
	*err = errormsg(msiSudoObjAclSet(1, "read", *researchGroup, *path, *aclKv), *msg);
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

# \brief iiRevokeReadAccessToResearchGroup  Rule to revoke read access to the vault package managed by a datamanger
# \param[in] path 
# \param[out] status
# \param[out] statusInfo
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
	*err = errormsg(msiSudoObjAclSet(1, "null", *researchGroup, *path, *aclKv), *msg);
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

# 
# \brief iiCopyACLsFromParent   When inheritance is missing we need to copy ACL's when introducing new data in vault package.
# \param[in] path 	path of object that needs the permissions of parent
iiCopyACLsFromParent(*path) {
	
	uuChopPath(*path, *parent, *child);

	foreach(*row in SELECT COLL_ACCESS_NAME, COLL_ACCESS_USER_ID WHERE COLL_NAME = *parent) {
		*accessName = *row.COLL_ACCESS_NAME;
		*userId = *row.COLL_ACCESS_USER_ID;
		foreach(*user in SELECT USER_NAME WHERE USER_ID = *userId) {
			*userName = *user.USER_NAME;
		}
		if (*accessName == "own") {
			writeLine("serverLog", "iiCopyACLsFromParent: granting own to *userName on *path");
			msiSetACL("default", "own", *userName, *path);
		} else if (*accessName == "read object") {
			writeLine("serverLog", "iiCopyACLsFromParent: granting read to *userName on *path");
			msiSetACL("default", "read", *userName, *path);
		} else if (*accessName == "modify object") {
			writeLine("serverLog", "iiCopyACLsFromParent: granting write to *userName on *path");
			msiSetACL("default", "write", *userName, *path);
		}
	}

}


# \brief iiFrontEndSystemMetadata Make system metadata accesible conform standard to the front end.
# \param[in] vaultPackage Package in the vault to retrieve system metadata from
# \param[out] result
# \param[out] status
# \param[out] statusInfo
iiFrontEndSystemMetadata(*vaultPackage, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = *folder;
	*result = "[]";
	*size = 0;

	# Package size
        iiFileCount(*vaultPackage, *totalSize, *dircount, *filecount, *modified);
        *unit = "bytes";
        if (*totalSize > 10000) {
                *totalSize = *totalSize / 1000;
                *unit = "KB";
        }
        if (*totalSize > 10000000) {
                *totalSize = *totalSize / 1000000;
                *unit = "MB";
        }
        if (*totalSize > 10000000000) {
                *totalSize = *totalSize / 1000000000;
                *unit = "GB";
	}
        *totalSize = floor(*totalSize);

	# Don't count vault package.
	*dircount = int(*dircount) - 1;

	*packageSizeArr = "[]";
	msi_json_arrayops(*packageSizeArr, "Package size", "add", *size);
	msi_json_arrayops(*packageSizeArr, "*filecount files, *dircount directories, total of *totalSize *unit", "add", *size);
	msi_json_arrayops(*result, *packageSizeArr, "add", *size);


        # Modified date
	*modifiedDate = "null";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = "org_publication_lastModifiedDateTime") {
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
	        msi_json_arrayops(*modifiedDateArr, "Modifed date", "add", *size);
	        msi_json_arrayops(*modifiedDateArr, "*date *time UTC*sign*zone", "add", *size);
	        msi_json_arrayops(*result, *modifiedDateArr, "add", *size);
	}


        # Package DOI
	*yodaDOI = "null";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = "org_publication_yodaDOI") {
		*yodaDOI = *row.META_COLL_ATTR_VALUE;
	}

	if (*yodaDOI != "null") {
	        *packageDOIArr = "[]";
	        msi_json_arrayops(*packageDOIArr, "Peristent Identifier", "add", *size);
	        msi_json_arrayops(*packageDOIArr, "DOI: *yodaDOI", "add", *size);
	        msi_json_arrayops(*result, *packageDOIArr, "add", *size);
	}


        # Landingpage URL
	*landingpageURL = "null";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = "org_publication_landingPageUrl") {
		*landingpageURL = *row.META_COLL_ATTR_VALUE;
	}

	if (*landingpageURL != "null") {
                *landinpageURLArr = "[]";
	        msi_json_arrayops(*landinpageURLArr, "Landingpage URL", "add", *size);
	        msi_json_arrayops(*landinpageURLArr, *landingpageURL, "add", *size);
	        msi_json_arrayops(*result, *landinpageURLArr, "add", *size);
	}
}

# iiCopyLicenseToVaultPackage     When a license is added to the metadata and it is available in the License collection,
#                                 this will copy the text to the package in the vault
# \param[in] folder  	          folder to copy to the vault
# \param[in] target               path of the vault package
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
}

