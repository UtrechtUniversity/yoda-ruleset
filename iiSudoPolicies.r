acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	ON (*otherName like regex "(datamanager|research)-.*") {
		iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
	}
}
