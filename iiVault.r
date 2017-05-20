iiCopyFolderToVault(*folder) {
	*err = errorcode(iiCollectionGroupName(*folder, *groupName));
	if (*err < 0) {
		failmsg(-1, "NoResearchGroup");
	}
	uuChop(*groupName, *_, *baseName, "-", true);
	uuChopPath(*folder, *parent, *datapackageName);
	msiGetIcatTime(*timestamp, "unix");
        *vaultGroupName = "vault-*baseName";
	*target = "/$rodsZoneClient/home/*vaultGroupName/*datapackageName" ++ "_*timestamp";
	*buffer.source = *folder;
	*buffer.destination = *target;
	uuTreeWalk("forward", *folder, "iiIngestObject", *buffer, *error);
	iiCopyRelevantMetadata(*folder, *target);
	iiFolderSecure(*folder);
}

iiIngestObject(*itemParent, *itemName, *itemIsCollection, *buffer) {
	*sourcePath = "*itemParent/*itemName";
	*destPath = *buffer.destination;
	if (*sourcePath != *buffer."source") {
		# rewrite path to copy objects that are located underneath the toplevel collection
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
	}
	if (*itemIsCollection) {
		msiCollCreate(*destPath, "1", *status);
	} else {
		msiDataObjChksum(*sourcePath, "forceChksum=", *checksum);
		msiDataObjCopy(*sourcePath, *destPath, "verifyChksum=", *status);
	}

}

iiCopyRelevantMetadata(*source, *destination) {
	*userMetadataPrefix = UUUSERMETADATAPREFIX ++ "%";
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
			WHERE COLL_NAME = *source
			AND META_COLL_ATTR_NAME like *userMetadataPrefix) {
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *row.META_COLL_ATTR_NAME, *row.META_COLL_ATTR_VALUE);
		msiAssociateKeyValuePairsToObj(*kvp, *destination, "-C");
	}

	*actionLog = UUORGMETADATAPREFIX ++ "action_log";	
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
	       		WHERE META_COLL_ATTR_NAME = *actionLog
		       	AND COLL_NAME = *source) {
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *row.META_COLL_ATTR_NAME, *row.META_COLL_ATTR_VALUE);
		msiAssociateKeyValuePairsToObj(*kvp, *destination, "-C");
	}
}
