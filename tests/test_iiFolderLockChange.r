testRule {
	iiFolderLockChange(*rootCollection, bool(*lockIt), *status);
}

input *rootCollection="", *lockIt=0
output ruleExecOut
