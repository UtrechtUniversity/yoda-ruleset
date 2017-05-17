testRule {
	*policyKv.actor = uuClientFullName;
	*recursive = 0;
	*accessLevel = "write";
	
	iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);

}
input *objPath="", *otherName=""
output ruleExecOut
