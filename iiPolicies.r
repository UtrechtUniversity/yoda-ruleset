# Policies go in here!

acDataDeletePolicy {
	uuIiDisallowOperationIfLockedOrFrozen($collParentName, true);
	uuIiDisallowOperationIfLockedOrFrozen($collName, true);
}


acPreProcForCollCreate {
	uuIiDisallowOperationIfLockedOrFrozen($collParentName, true);
	uuIiDisallowOperationIfLockedOrFrozen($collName, true);
}

# only SuserAndConn available. Need information on object as well
# acPreProcForModifyAccessControl {

# }

# only SuserAndConn available. Need information on object as well
#acPreProcForModifyAVUMetadata {
#
#}

acPreProcForModifyCollMeta {
	uuIiDisallowOperationIfLockedOrFrozen($collParentName, true);
	uuIiDisallowOperationIfLockedOrFrozen($collName, true);
}

acPreProcForModifyDataObjMeta {
	uuIiDisallowOperationIfLockedOrFrozen($objPath, false);
}

acPreProcForObjRename {
	uuIiDisallowOperationIfLockedOrFrozen($objPath, false);
}

acPreProcForRmColl {
	uuIiDisallowOperationIfLockedOrFrozen($collParentName, true);
	uuIiDisallowOperationIfLockedOrFrozen($collName, true);
}

acPreProcForDataObjOpen {
	ON ($writeFlag == "1") {
		uuIiDisallowOperationIfLockedOrFrozen($objectPath, false);
	}
}

uuIiDisallowOperationIfLockedOrFrozen(*objectPath, *isCollection) {
	uuYcObjectIsLocked(*objPath, *locked);
	iiObjectIsSnapshotLocked(*objPath, *isCollection, *snaplocked, *frozen);

	if(*locked || *snaplocked || *frozen) {
		uuYcIsAdminUser(*isAdminUser);
		if(!*isAdminUser) {
			cut;
			msiOprDisallowed;
		}
	}
}