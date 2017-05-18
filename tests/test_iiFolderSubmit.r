testRule {
   iiFolderSubmit(*folder, *folderStatus, *status, *statusInfo);
	writeLine("stdout", *status);
	if (*status != "Success") {
	   writeLine("stdout", *statusInfo);
	}
	writeLine("stdout", *folderStatus);

}
input *folder=""
output ruleExecOut
