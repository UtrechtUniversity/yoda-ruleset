acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	ON (*otherName like regex "(datamanager|research|read)-.*") {
		iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
	}
}
