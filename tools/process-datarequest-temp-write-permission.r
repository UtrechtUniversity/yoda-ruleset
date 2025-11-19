#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F
processTempWritePermission() {
    uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

    if (*usertype != "rodsadmin") {
        failmsg(-1, "This script needs to be run by a rodsadmin");
    }

    if (*permission == "grant") {
        msiSetACL("default", "admin:write", *user, *path);
    } else if (*permission == "grantread") {
        msiSetACL("default", "admin:read", *user, *path);
    } else if (*permission == "own") {
        msiSetACL("default", "admin:own", *user, *path);
    } else if (*permission == "revoke") {
        msiSetACL("default", "admin:null", *user, *path);
    } else {
        writeLine("stdout", "processTempWritePermission: invalid permission value");
        *status = "InternalError";
        *statusInfo = "";
    }
}

input *actor="", *path="", *permission="", *user=""
output ruleExecOut
