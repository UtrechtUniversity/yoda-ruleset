testRule {
	iiFolderReject(*folder, *status, *statusInfo);
	writeLine("stdout", *status);
	if (*status != "Success") {
	   writeLine("stdout", *statusInfo);
	}
}
input *folder=""
output ruleExecOut
