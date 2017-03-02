iiPreCollCreate(*path, *user) {
	writeLine("serverLog", "iiPreCollCreate(*path, *user)");

	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if (*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks."*lockName";
			if (strlen(*rootCollection) > strlen(*parent)) {
				writeLine("serverLog", "iiPreCollCreate: lock *lockName found. But Starting from *rootCollection") ;
			} else {
				fail;
			}
		}
	}
}

iiPreCollRename(*src, *dst, *user) {
	writeLine("serverLog", "iiPreCollRename(*src, *dst, *user)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*src, *locks, *locked);
	if(*locked) {
		fail;
	}

}

iiPreCollDelete(*path, *user) {
	writeLine("serverLog", "iiPreCollDelete(*path, *user)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		fail;
	}
}

iiPreDataObjCreate(*path, *user) {
	writeLine("serverLog", "iiPreDataObjCreate(*path, *user)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if(*locked) {
		fail;
	}
}

iiPreDataObjWrite(*path, *user) {
	writeLine("serverLog", "iiPreDataObjWrite(*path, *user)"); 
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		fail;
	}
}

iiPreDataObjRename(*src, *dst, *user) {
	writeLine("serverLog", "iiPreDataObjRename(*src, *dst, *user)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		fail;
	}

}

iiPreDataObjDelete(*path, *user) {
	writeLine("serverLog", "iiPreDataObjDelete(*path, *user)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		fail;
	}

}

iiPreCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName) {
	writeLine("serverLog", "iiPreCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName)");

	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}
	
	iiGetLocks(*sourceItemName, *locks, *locked);
	if (*locked) {
		fail;
	}
	
	iiGetLocks(*targetItemName, *locks, *locked);
	if (*locked) {
		fail;
	}

}

iiPreModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
	writeLine("serverLog", "iiPreModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit)");
	
	uuGetUserType(*user, *userType);
	if (*userType == "rodsadmin") {
		succeed;
	}

	iiGetLocks(*itemName, *locks, *locked);
	if (*locked) {
		if (*itemType == "-C") {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*parent)) {
					writeLine("serverLog", "iiPreCollCreate: lock *lockName found, but Starting from *rootCollection") ;
				} else {
					fail;
				}
			}
		} else {
			fail;
		}
	}
}

iiPreModifyOrgMetadata(*option, *itemType, *itemName, *attributeName) {
	writeLine("serverLog", "iiPreModifyOrgMetadata(*option, *itemType, *itemName, *attributeName)");
	# Locking org metadata would prevent unlocking.
	succeed;

}

iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue) {
	writeLine("serverLog", "iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue)");
	if (*option == "rm") {
		if (!iiIsStatusTransitionLegal(*attributeValue, UNPROTECTED)) {
			fail;
		}
	}
	if (*option == "add") {
		
		if (!iiIsStatusTransitionLegal(UNPROTECTED, *attributeValue)) {
			fail;
		}
	}
	if (*option == "set") {
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = *attributeName) {
			if(!iiIsStatusTransitionLegal(*row.META_COLL_ATTR_VALUE, *attributeValue)) {
				fail;
			}
		}
	}
}

iiPreModifyFolderStatus(*option, *path, *attributeName, *newAttributeName, *attributeValue, *newAttributeValue) {
	writeLine("serverLog", "iiPreModifyFolderStatus(*option, *path, *attributeName, *newAttributeName, *attributeValue, *newAttributeValue)");

}
