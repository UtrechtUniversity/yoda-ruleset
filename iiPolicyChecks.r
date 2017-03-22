# \brief iiRenameInvalidXML
iiRenameInvalidXML(*xmlpath, *xsdpath) {
		*invalid = false;
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
			*invalid = true;
		} else {
			msiBytesBufToStr(*status_buf, *status_str);
			*len = strlen(*status_str);
			if (*len == 0) {
				writeLine("serverLog", "XSD validation returned no output. This implies successful validation.");
			} else {
				writeBytesBuf("serverLog", *status_buf);
				*invalid = true;
			}
		}
		if (*invalid) {
			writeLine("serverLog", "Renaming corrupt or invalid $objPath");
			msiGetIcatTime(*timestamp, "unix");
			*iso8601 = uuiso8601(*timestamp);
			msiDataObjRename(*xmlpath, *xmlpath ++ "_invalid_" ++ *iso8601, 0, *status_rename);
		}
}

# \brief iiIsStatusTransitionLegal
iiIsStatusTransitionLegal(*fromstatus, *tostatus) {
	*legal = false;
	foreach(*legaltransition in IIFOLDERTRANSITIONS) {
		(*legalfrom, *legalto) = *legaltransition;
		if (*legalfrom == *fromstatus && *legalto == *tostatus) {
			*legal = true;
			break;
		}
	}
	*legal;
}

# \brief iiGetLocks
iiGetLocks(*objPath, *locks, *locked) {
	*locked = false;
	*lockprefix = UUORGMETADATAPREFIX ++ "lock_";
	msiGetObjType(*objPath, *objType);
	msiString2KeyValPair("", *locks);
	if (*objType == '-d') {
		uuChopPath(*objPath, *collection, *dataName);
		foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
					WHERE COLL_NAME = '*collection'
					  AND DATA_NAME = '*dataName'
					  AND META_DATA_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = triml(*row.META_DATA_ATTR_NAME, *lockprefix);
			*rootCollection= *row.META_DATA_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, *lockName, *valid);
			writeLine("serverLog", "iiGetLocks: *objPath -> *lockName=*rootCollection [valid=*valid]");
			if (*valid) {
				*locks."*lockName" = *rootCollection;
				*locked = true;
			}
		}
	} else {
		foreach (*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
					WHERE COLL_NAME = '*objPath'
					  AND META_COLL_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = triml(*row.META_COLL_ATTR_NAME, *lockprefix);
			*rootCollection = *row.META_COLL_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, *lockName, *valid);
			writeLine("serverLog", "iiGetLocks: *objPath -> *lockName=*rootCollection [valid=*valid]");
			if (*valid) {
				*locks."*lockName" = *rootCollection;
				*locked = true;
			}
		}
	}
}

# \brief iiCanCollCreate 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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

# \brief iiCanCollRename 
# \param[in] src
# \param[in] dst
# \param[out] allowed
# \param[out] reason
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
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent renaming subcollections."
				} else {
					*allowed = false;
					*reason = "*dstparent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No Locks found";
		}
	}

	writeLine("serverLog", "iiCanCollRename: *src -> *dst; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjCreate(*path, *allowed, *reason) {
	
	*allowed = false;
	*reason = "Unknown error";

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if(*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks."*lockName";
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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
				*rootCollection = *locks."*lockName";
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjRename(*src, *dst, *allowed, *reason) {

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
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent writing to files."
				} else {
					*allowed = false;
					*reason = "*dstparent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}

	writeLine("serverLog", "iiCanDataObjRename: *src -> *dst; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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
	} else {
		*allowed = true;
		*reason = "No locks found";
	}

	writeLine("serverLog", "iiCanModifyUserMetadata: *itemName; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = true;
	*reason = "No reason to lock OrgMetatadata yet";
	writeLine("serverLog", "iiCanModifyOrgMetadata: *itemName; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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
		*transitionFrom = "";
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = *attributeName) {
			*transitionFrom = *row.META_COLL_ATTR_VALUE;
		}

		*transitionTo = *attributeValue;	

		if (*transitionFrom == "") {
			*transitionFrom = UNPROTECTED;
		}
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

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
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
