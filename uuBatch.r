# \file      uuBatch.r
# \brief     Batch functionality.
# \author    Felix Croes
# \copyright Copyright (c) 2022, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


verifyChecksumBatch(*start, *max, *update) {
    *bucket = 0;
    foreach (*row in SELECT ORDER(DATA_ID),COLL_NAME,DATA_NAME,DATA_SIZE,DATA_CHECKSUM WHERE COLL_NAME LIKE '/$rodsZoneClient/home/vault%' AND DATA_ID >= '*start') {
	*coll = *row.COLL_NAME;
	*data = *row.DATA_NAME;
	verifyChecksumData("*coll/*data", *row.DATA_CHECKSUM, *update);

	*bucket = *bucket + int(*row.DATA_SIZE);
	if (*bucket >= *max) {
	    *start = int(*row.DATA_ID) + 1;
	    delay ("<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>1s</PLUSET>") {
		verifyChecksumBatch(*start, *max, *update);
	    }
	    break;
	}
    }
}

verifyChecksumData(*path, *chksum, *update) {
    msiCheckAccess(*path, "read_object", *access);
    if (*access == 0) {
	msiSetACL("default", "admin:read", uuClientFullName, *path);
    }

    if (*chksum == "") {
	writeLine("serverLog", "*path: no checksum");
	if (*update != 0) {
	    errorcode(msiDataObjChksum(*path, "ChksumAll=", *status));
	}
    } else {
	msiSubstr(*chksum, "0", "5", *type);
	writeLine("serverLog", "*path: *chksum");
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
