testRule {
	uuAclListOfPath(*pathA, *aclListA);
	writeLine("stdout", "aclListA\n----");
	foreach(*acl in *aclListA) {
		uuAclToStrings(*acl, *userName, *accessLevel);
		writeLine("stdout", "*acl: *userName, *accessLevel");
	}

	uuAclListOfPath(*pathB, *aclListB);
	writeLine("stdout", "----\naclListB\n----");
	foreach(*acl in *aclListB) {
		uuAclToStrings(*acl, *userName, *accessLevel);
		writeLine("stdout", "*acl: *userName, *accessLevel");
	}

	uuAclListSetDiff(*aclListA, *aclListB, *setDiffA);
	writeLine("stdout", "----\nsetDiffA\n----");
	foreach(*acl in *setDiffA) {
		uuAclToStrings(*acl, *userName, *accessLevel);
		writeLine("stdout", "*acl: *userName, *accessLevel");
	}

	uuAclListSetDiff(*aclListB, *aclListA, *setDiffB);
	writeLine("stdout", "----\nsetDiffB\n----");
	foreach(*acl in *setDiffB) {
		uuAclToStrings(*acl, *userName, *accessLevel);
		writeLine("stdout", "*acl: *userName, *accessLevel");
	}


}
input *pathA="", *pathB=""
output ruleExecOut
