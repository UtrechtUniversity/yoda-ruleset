testRule {
	iiFolderApprove(*folder, *status, *statusInfo);
	writeLine("stdout", *status);
	if (*status != "Success") {
	   writeLine("stdout", "statusInfo: *statusInfo");
	}
}
input *folder=""
output ruleExecOut
