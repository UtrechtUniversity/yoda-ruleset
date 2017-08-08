testRule {
	iiListLocks(*path, *offset, *limit, *result, *status, *statusInfo); 
	writeLine("stdout", "*status - *statusInfo");
	writeLine("stdout", *result);
}
input *path="", *offset=0, *limit=10
output ruleExecOut
