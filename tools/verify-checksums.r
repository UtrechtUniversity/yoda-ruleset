#!/usr/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance -F 
#
# Verify, and optionally set, checksums.
#
# usage: irule -F verify-checksums.r
#        irule -F verify-checksums.r "*update=1"
#
verifyChecksums() {
    # all collections under home
    foreach (*row in SELECT COLL_NAME WHERE COLL_NAME like '/$rodsZoneClient/home/%') {
	collChecksums(*row.COLL_NAME, *update);
    }
}

collChecksums(*coll, *update) {
    # check data objects in collection
    foreach (*data in SELECT DATA_NAME,DATA_CHECKSUM WHERE COLL_NAME = *coll) {
	*name = *data.DATA_NAME;
	dataChecksum("*coll/*name", *data.DATA_CHECKSUM, *update);
    }
}

dataChecksum(*path, *chksum, *update) {
    msiCheckAccess(*path, "read object", *access);
    if (*access == 0) {
	msiSetACL("default", "admin:read", uuClientFullName, *path);
    }

    if (*chksum == "") {
	writeLine("stdout", "*path: no checksum");
	if (*update != 0) {
	    errorcode(msiDataObjChksum(*path, "ChksumAll=", *status));
	}
    } else {
	msiSubstr(*chksum, "0", "5", *type);
	writeLine("stdout", "*path: *chksum");
	if (*type == "sha2:") {
	    errorcode(msiDataObjChksum(*path, "verifyChksum=", *status));
	} else if (*update != 0) {
	    errorcode(msiDataObjChksum(*path, "ChksumAll=++++forceChksum=", *status));
	}
    }

    if (*access == 0) {
	msiSetACL("default", "admin:null", uuClientFullName, *path);
    }
}

input *update=0
output ruleExecOut
