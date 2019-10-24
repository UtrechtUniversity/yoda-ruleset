testRule {
   iiFolderSubmit(*folder, *folderStatus, *status, *statusInfo);
	writeLine("stdout", *status);
	if (*status != "Success") {
	   writeLine("stdout", "statusInfo: *statusInfo");
	}
	writeLine("stdout", "folderStatus: *folderStatus");
}
input *folder=""
output ruleExecOut
