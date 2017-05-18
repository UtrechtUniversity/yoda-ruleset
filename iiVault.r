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
	
	iiFolderSecure(*folder);
}
