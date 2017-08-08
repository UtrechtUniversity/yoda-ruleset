migrateLocks {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);
	writeLine("stdout", "Usertype: *usertype");

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	*researchGroups = "/$rodsZoneClient/home/research-";
	foreach(*row in SELECT COLL_NAME WHERE COLL_NAME like "*researchGroups%") {
		*collName = *row.COLL_NAME;
		msiSetACL("default", "admin:write", $userNameClient, *collName);
	}

	foreach(*row in SELECT COLL_NAME, META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = 'org_lock_protect') {
		*collName = *row.COLL_NAME;
		*rootCollection = *row.META_COLL_ATTR_VALUE;
		msiString2KeyValPair("", *newLock);
		*newLock.org_lock = *rootCollection;
		msiAssociateKeyValuePairsToObj(*newLock, *collName, "-C") ::: succeed;
		msiString2KeyValPair("", *oldLock);
		*oldLock.org_lock_protect = *rootCollection;
		msiRemoveKeyValuePairsFromObj(*oldLock, *collName, "-C");
		writeLine("stdout", "*collName *oldLock -> *newLock");
	}

	foreach(*row in SELECT COLL_NAME, DATA_NAME, META_DATA_ATTR_VALUE WHERE META_DATA_ATTR_NAME = 'org_lock_protect') {
		*collName = *row.COLL_NAME;
		*dataName = *row.DATA_NAME;
		*path = "*collName/*dataName";
		*rootCollection = *row.META_DATA_ATTR_VALUE;
		msiString2KeyValPair("", *newLock);
		*newLock.org_lock = *rootCollection;
		msiAssociateKeyValuePairsToObj(*newLock, *path, "-d") ::: succeed;
		msiString2KeyValPair("", *oldLock);
		*oldLock.org_lock_protect = *rootCollection;
		msiRemoveKeyValuePairsFromObj(*oldLock, *path, "-d");
		writeLine("stdout", "*path *oldLock -> *newLock");
	}

	msiString2KeyValPair("org_status=LOCKED", *newStatus);
	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_status' AND META_COLL_ATTR_VALUE = 'PROTECTED') {
		*collName = *row.COLL_NAME;
		msiSetKeyValuePairsToObj(*newStatus, *collName, "-C");
		writeLine("stdout", "*collName org_status=PROTECTED -> org_status=LOCKED");
	}		
	
	foreach (*row in SELECT COLL_NAME, DATA_NAME WHERE META_DATA_ATTR_NAME = 'org_status' AND META_DATA_ATTR_VALUE = 'PROTECTED') {
		*collName = *row.COLL_NAME;
		*dataName = *row.DATA_NAME;
		*path = "*collName/*dataName";
		msiSetKeyValuePairsFromObj(*newStatus, *path, "-d");
		writeLine("stdout", "*path org_status=PROTECTED -> org_status=LOCKED");
	}

	msiString2KeyValPair("org_status=UNPROTECTED", *oldStatus);
	foreach (*row in SELECT COLL_NAME WHERE META_COLL_ATTR_NAME = 'org_status' AND META_COLL_ATTR_VALUE = 'UNPROTECTED') {
		*collName = *row.COLL_NAME;
		msiRemoveKeyValuePairsFromObj(*oldStatus, *collName, "-C");
		writeLine("stdout", "*collName Remove org_status=UNPROTECTED");
	}		
	
	foreach (*row in SELECT COLL_NAME, DATA_NAME WHERE META_DATA_ATTR_NAME = 'org_status' AND META_DATA_ATTR_VALUE = 'UNPROTECTED') {
		*collName = *row.COLL_NAME;
		*dataName = *row.DATA_NAME;
		*path = "*collName/*dataName";
		msiRemoveKeyValuePairsFromObj(*oldStatus, *path, "-d");
		writeLine("stdout", "*path Remove org_status=UNPROTECTED");
	}

}

input null
output ruleExecOut
