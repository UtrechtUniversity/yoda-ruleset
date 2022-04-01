processTempWritePermission() {

	if (*permission == "grant") {
		msiSetACL("default", "write", *user, *path);
        } else if (*permission == "grantread") {
                msiSetACL("default", "read", *user, *path);
        } else if (*permission == "own") {
                msiSetACL("default", "own", *user, *path);
	} else if (*permission == "revoke") {
		msiSetACL("default", "null", *user, *path);
	} else {
		writeLine("stdout", "processTempWritePermission: invalid permission value");
		*status = "InternalError";
		*statusInfo = "";
	}
}
input *actor="", *path="", *permission="", *user=""
output ruleExecOut
