testRule {
	iiFolderLockChange(*rootCollection, *lockName, *lockIt, *status);
}

input *rootCollection="", *lockName="", *lockIt=false
output ruleExecOut
