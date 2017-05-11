
acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-c") {
		iiDatamanagerPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv);
	}
}


acPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {
        ON (*objType == "-c") {
                iiDatamanagerPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv);
        }
}

acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	ON (*otherName like "datamanager-*") {
		iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
	}
}
