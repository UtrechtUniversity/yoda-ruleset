adminTapeArchiveSetState() {
	writeLine("serverLog", "PATH: *path TIMESTAMP: *timestamp STATE: *state");

    # Check if rods can modify metadata and grant temporary write ACL if necessary.
    msiCheckAccess(*path, "modify metadata", *modifyPermission);
    if (*modifyPermission == 0) {
        writeLine("stdout", "Granting write access to *path");
        msiSetACL("default", "admin:write", uuClientFullName, *path);
    }

    # Set tape archive timestamp and state.
    *tape_archive_time = UUORGMETADATAPREFIX ++ "tape_archive_time=" ++ *timestamp;
    msiString2KeyValPair(*tape_archive_time, *tape_archive_time_kvp);
    msiSetKeyValuePairsToObj(*tape_archive_time_kvp, *path, "-d");

    *tape_archive_state = UUORGMETADATAPREFIX ++ "tape_archive_state=" ++ *state;
    msiString2KeyValPair(*tape_archive_state, *tape_archive_state_kvp);
    msiSetKeyValuePairsToObj(*tape_archive_state_kvp, *path, "-d");

    # Remove the temporary write ACL.
    if (*modifyPermission == 0) {
        writeLine("stdout", "Revoking write access to *path");
        msiSetACL("default", "admin:null", uuClientFullName, *path);
    }
}
input *path="", *timestamp="", *state=""
output ruleExecOut
