processTempWritePermission() {

	if (*permission == "grant") {
		msiSetACL("default", "write", *actor, *path);
	} else if (*permission == "revoke") {
		msiSetACL("default", "null", *actor, *path);
	} else {
		writeLine("stdout", "processTempWritePermission: invalid permission value");
		*status = "InternalError";
		*statusInfo = "";
	}
}
input *actor="", *path="", *permission=""
output ruleExecOut
