acPreprocForRmColl {
        uuIiObjectActionAllowed($collName, *collAllows);
        uuIiObjectActionAllowed($collParentName, *parentAllows);
        writeLine("serverLog", "Requesting deleting of collection '$collName'. Can delete? *collAllows. Parent allows? *parentAllows");
        if(!(*collAllows && *parentAllows)) {
                writeLine("serverLog", "Disallowing deleting $collName");
                cut;
                msiDeleteDisallowed();
        }
}

acDataDeletePolicy {
        writeLine("serverLog", "Requested deleting of file:");
        uuIiObjectActionAllowed($objPath, *allow);
        if(!*allow) {
                writeLine("serverLog", "Deleting $objPath not allowed");
                cut;
                msiDeleteDisallowed();
        }
}

acPreprocForCollCreate {
        uuIiObjectActionAllowed($collParentName, *allowed);
        writeLine("serverLog", "Requesting creating collection $collName. Allowed = *allowed");
        if(!*allowed) {
                writeLine("serverLog", "Disallowing creating $collName collection");
                cut;
                msiOprDisallowed;
        }
}

acPreProcForObjRename(*source, *destination) {
        uuChopPath(*source, *sourceParent, *sourceBase);
        uuChopPath(*destination, *destParent, *destBase);
        uuIiObjectActionAllowed(*source, *sourceAllows);
        uuIiObjectActionAllowed(*sourceParent, *sourceParentAllows);
        uuIiObjectActionAllowed(*destParent, *destAllows);
        writeLine("serverLog", "Requesting moving *source to *destination. Source allows = *sourceAllows, parent allows = *sourceParentAllows, destination allows = *destAllows");
        if(!(*sourceAllows && *sourceParentAllows && *destAllows)) {
                writeLine("serverLog", "Disallowing moving *source to *destination");
                cut;
                msiOprDisallowed;
        }
}

acPreprocForDataObjOpen {
        ON ($writeFlag == "1") {
                uuIiObjectActionAllowed($objPath, *objAllows);
                if(!*objAllows) {
                        writeLine("serverLog", "Disallowing opening $objPath for writing");
                        cut;
                        msiOprDisallowed;
                }
        }
}

acSetRescSchemeForCreate {
        uuChopPath($objPath, *parent, *base);
        uuIiObjectActionAllowed(*parent, *allowed);
        if(!*allowed) {
                writeLine("serverLog", "Creating data object $objPath not allowed");
                cut;
                msiOprDisallowed;
        }
        msiSetDefaultResc("$destRescName", "null");
}

uuIiObjectActionAllowed(*objPath, *allowed) {
        *allowed = true;
        msiGetObjType(*objPath, *type);
        *isCollection = false;
        if (*type == "-c") {
                *isCollection = true;
        }
        uuLockExists(*objPath, *locked);
        iiObjectIsSnapshotLocked(*objPath, *isCollection, *snaplocked, *frozen);
        writeLine("serverLog", "*objPath (isCollection=*isCollection) is snapshotLocked=*snaplocked, frozen=*frozen");
        if(*locked || *snaplocked || *frozen) {
                uuYcIsAdminUser(*isAdminUser);
                if(!*isAdminUser) {
                        *allowed = false;
                }
        }
}
