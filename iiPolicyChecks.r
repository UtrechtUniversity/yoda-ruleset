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


iiHasLock(*objPath) {
	*lockprefix = UUORGMETADATAPREFIX ++ "lock_";
	msiGetObjType(*objPath, *objType);
	*locked = false;
	if (*objType == '-d') {
		uuChopPath(*objPath, *collection, *dataName);
		foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
					WHERE COLL_NAME = '*collection'
					  AND DATA_NAME = '*dataName'
					  AND META_DATA_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = *row.META_DATA_ATTR_NAME;
			*lockTimestamp = *row.META_DATA_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, triml(*lockName, *lockprefix), *valid);
			writeLine("serverLog", "iiHasLock: *objPath -> *lockName=*lockTimestamp [valid=*valid]");
			if (*valid) {
				*locked = true;
				break;
			}
		}
	} else {
		foreach (*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
					WHERE COLL_NAME = '*objPath'
					  AND META_COLL_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = *row.META_COLL_ATTR_NAME;
			*lockTimestamp = *row.META_COLL_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, triml(*lockName, *lockprefix), *valid);
			writeLine("serverLog", "iiHasLock: *objPath -> *lockName=*lockTimestamp [valid=*valid]");
			if (*valid) {
				*locked = true;
				break;
			}
		}
	}
	*locked;
}


iiObjectActionAllowed(*path, *allowed, *clientFullName) {
	*allowed = false;
	uuGetUserType(*clientFullName, *userType);
	if (*userType == "rodsadmin" ) {
		*allowed = true;
	} else if (!iiHasLock(*path)) {
		*allowed = true;
	}
		
	writeLine("serverLog", "iiObjectActionAllowed: *path allowed=*allowed");
}

iiObjectActionAllowed(*path, *allowed) {
	*clientFullName  = uuClientFullName();
	iiObjectActionAllowed(*path, *allowed, *clientFullName);
}
