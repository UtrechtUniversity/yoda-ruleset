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
			*lockName = triml(*row.META_COLL_ATTR_NAME, *lockprefix);
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

iiCollectionModifyAllowed(*path, *allowed) {
	uuGetUserType(uuClientFullName, *userType);
	iiCollectionModifyAllowed(*userType, *path, *allowed);
}

iiCollectionModifyAllowed(*userType, *path, *allowed) {
	*allowed = false;
	*reason = "unknown";
	if (*userType == "rodsadmin" ) {
		*reason = "*clientFullName is rodsadmin";
		*allowed = true;
	} else {
		iiGetLocks(*path, *locks, *locked);
		foreach(*lock in *locks) {
				*rootCollection = *locks."*lock";
				if (strlen(*rootCollection) > strlen(*path)) {
					*reason = "subfolder *rootCollection is *lock locked.";
						allowed = false;
						break;
				} else {
					*reason = "*rootCollection is *lock locked";
					*allowed = false;
					break;
				}	
		}
	}
		
	writeLine("serverLog", "iiObjectActionAllowed: *path allowed=*allowed reason=*reason");
}

iiObjectActionAllowed(*path, *allowed) {
	uuGetUserType(uuClientFullName, *userType);
	iiObjectActionAllowed(*userType, *path, *allowed);
}

iiObjectActionAllowed(*userType, *path, *allowed) {
	*allowed = false;
	if (*userType == "rodsadmin" ) {
		*reason = "*clientFullName is rodsadmin";
		*allowed = true;
	} else {
		iiGetLocks(*path, *locks, *locked);

		if (*locked) {
			foreach(*lock in *locks) {
				*rootCollection = *locks."*lock";
				if (strlen(*rootCollection) > strlen(*path)) {
					*reason = "Child *rootCollection has *lock lock. Does not affect current action.";
					*allowed = true;
				} else {
					*reason = "*lock lock found at *rootCollection";
					*allowed = false;
					break;
				}
			}
		} else {
			*reason = "No locks found on *path";
			*allowed = true;		
		}
	}
	writeLine("serverLog", "iiObjectActionAllowed: *path allowed=*allowed reason=*reason");
}
