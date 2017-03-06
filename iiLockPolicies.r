iiCanCollCreate(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown failure";

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if (*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks."*lockName";
			if (strlen(*rootCollection) > strlen(*parent)) {
				*reason = "lock *lockName found on *parent, but Starting from *rootCollection" ;
				*allowed = true;
			} else {
				*reason = "lock *lockName found on *parent. Disallowing creating subcollection: *basename";
				*allowed = false;
				break;
			}
		}
	} else {
		*reason = "No locks found on *parent";
		*allowed = true;
	}

	writeLine("serverLog", "iiCanCollCreate: *path; allowed=*allowed; reason=*reason");
}

iiCanCollRename(*src, *dst, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "*src is has locks *locks";	
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks, *locked);
		if (*locked) {
			*allowed = false;
			*reason = "*dstparent has locks *locks";
		} else {
			*allowed = true;
			*reason = "No Locks found";
		}
	}

	writeLine("serverLog", "iiCanCollRename: *src -> *dst; allowed=*allowed; reason=*reason");
}

iiCanCollDelete(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown error"; 	
	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "Locked with *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}

	writeLine("serverLog", "iiCanCollDelete: *path; allowed=*allowed; reason=*reason");
}

iiCanDataObjCreate(*path, *allowed, *reason) {
	
	*allowed = false;
	*reason = "Unknown error";

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if(*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks.*lockName;
			if (strlen(*rootCollection) > strlen(*parent)) {
				*allowed = true;
				*reason = "*parent has locked child *rootCollection, but this does not prevent creating new files."
			} else {
				*allowed = false;
				*reason = "*parent has lock(s) *locks";
				break;
			}
		}
	} else {
		*allowed = true;
		*reason = "No locks found";
	}

	writeLine("serverLog", "iiCanDataObjCreate: *path; allowed=*allowed; reason=*reason");
}

iiCanDataObjWrite(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown error";

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "Locks found: *locks";
	} else  {
		uuChopPath(*path, *parent, *basename);
		iiGetLocks(*parent, *locks, *locked);
		if(*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks.*lockName;
				if (strlen(*rootCollection) > strlen(*parent)) {
					*allowed = true;
					*reason = "*parent has locked child *rootCollection, but this does not prevent writing to files."
				} else {
					*allowed = false;
					*reason = "*parent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}
	
	writeLine("serverLog", "iiCanDataObjWrite: *path; allowed=*allowed; reason=*reason");
}

iiCanDataObjRename(*src, *dst, *reason, *allowed) {

	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "*src is locked with *locks";
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks, *locked);
		if(*locked) {
			*allowed = false;
			*reason = "*dstparent is locked with *locks";
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}

	writeLine("serverLog", "iiCanDataObjRename: *path; allowed=*allowed; reason=*reason");
}

iiCanDataObjDelete(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown Error";

	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*reason = "Found lock(s) *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	writeLine("serverLog", "iiCanDataObjDelete: *path; allowed=*allowed; reason=*reason");
}

iiCanCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName, *allowed, *reason) {	
	*allowed = false;
	*reason = "Unknown error";
	
	if (*targetItemType == "-C") {	
		# Prevent copying metadata to locked folder
		iiGetLocks(*targetItemName, *locks, *locked);
		if (*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*targetItemName)) {
					*allowed = true;
					*reason = "*rootCollection is locked, but does not affect metadata copy to *targetItemName";
				} else {
					*allowed = false;
				*reason = "*targetItemName is locked";	
				break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	} else if (*targetItemType == "-d") {
		   iiGetLocks(*targetItemName, *locks, *locked);
		if (*locked) {
			*reason = "*targetItemName has lock(s) *locks";
		} else {
			*allowed = true;
			*reason = "No locks found.";
		}
	} else {
		*allowed = true;
		*reason = "Restrictions only apply on Collections and DataObjects";
	}

	writeLine("serverLog", "iiCanCopyMetadata: *sourceItemName -> *targetItemName; allowed=*allowed; reason=*reason");
}

iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*itemName, *locks, *locked);
	if (*locked) {
		if (*itemType == "-C") {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*parent)) {
					*allowed = true;
					*reason = "Lock *lockName found, but starting from *rootCollection";
				} else {
					*allowed = false;
					*reason = "Lock *LockName found on *rootCollection";
					break;
				}
			}
		} else {
			*reason = "Locks found. *locks";	
		}
	}

	writeLine("serverLog", "iiCanModifyUserMetadata: *itemName; allowed=*allowed; reason=*reason");
}

iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = true;
	*reason = "No reason to lock OrgMetatadata yet";
	writeLine("serverLog", "iiCanModifyOrgMetadata: *itemName; allowed=*allowed; reason=*reason");
}

iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (*attributeName != UUORGMETADATAPREFIX ++ "status") {
		failmsg(-1, "iiCanModifyFolderStatus: Called for attribute *attributeName instead of FolderStatus.");
	}

	if (*option == "rm") {
		*transitionFrom = *attributeValue;
		*transitionTo =  UNPROTECTED;
	}

	if (*option == "add") {
		*transitionFrom = UNPROTECTED;
		*transitionTo = *attributeValue;	
	}

	if (*option == "set") {
		*transitionTo = *attributeValue;
		# We need to query for current status. Set to UNPROTECTED by default.
		*transitionFrom = UNPROTECTED;
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = *attributeName) {
			*transitionFrom = *row.META_COLL_ATTR_VALUE;
		}
	}

	if (!iiIsStatusTransitionLegal(*transitionFrom, *transitionTo)) {
		*reason = "Illegal status transition from *transitionFrom to *transitionTo";
	} else {
		*allowed = true;
		*reason = "Legal status transition. *transitionFrom -> *transitionTo";

		iiGetLocks(*path, *locks, *locked);
		if (*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (*rootCollection != *path) {
					*allowed = false;
					*reason = "Found lock(s) *lockName starting from *rootCollection";
					break;
				}
			}
		}

	}

	writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}

iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue, *allowed, *reason) {
	writeLine("serverLog", "iiCanModifyFolderStatus:*option, *path, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue");
	*allowed = false;
	*reason = "Unknown error";
	if (*newAttributeName == ""  || *newAttributeName == UUORGMETADATAPREFIX ++ "status") {
		*transitionFrom = *attributeValue;
		*transitionTo = triml(*newAttributeValue, "v:");
		if (!iiIsStatusTransitionLegal(*transitionFrom, *transitionTo)) {
			*reason = "Illegal status transition from *transitionFrom to *transitionTo";
		} else {
			*allowed = true;
			*reason = "Legal status transition. *transitionFrom -> *transitionTo";

			iiGetLocks(*path, *locks, *locked);
			if (*locked) {
				foreach(*lockName in *locks) {
					*rootCollection = *locks."*lockName";
					if (*rootCollection != *path) {
						*allowed = false;
						*reason = "Found lock(s) *lockName starting from *rootCollection";
						break;
					}
				}
			}
		}
	} else {
		*reason = "*attributeName should not be changed to *newAttributeName";
	}

	writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}
