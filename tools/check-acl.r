#!/usr/bin/irule -F
#
# Report, and optionally fix, bad ACLs for research and intake collections
#
# usage: check-acl
#        check-acl "*update=1"
#
checkACL() {
    # research collections
    foreach (*row in SELECT COLL_NAME WHERE COLL_NAME like '/$rodsZoneClient/home/research-%') {
	*coll = *row.COLL_NAME;
	if (*coll not like "/$rodsZoneClient/home/research\*/\*") {
	    checkCollACL(*coll, *update);
	}
    }

    # intake collections
    foreach (*row in SELECT COLL_NAME WHERE COLL_NAME like '/$rodsZoneClient/home/grp-intake-%') {
	*coll = *row.COLL_NAME;
	if (*coll not like "/$rodsZoneClient/home/grp-intake\*/\*") {
	    checkCollACL(*coll, *update);
	}
    }
}

checkCollACL(*topColl, *update) {
    # get access rights of collection
    *access = getCollAccess(*topColl);

    # check data objects in collection
    foreach (*data in SELECT DATA_NAME WHERE COLL_NAME = *topColl) {
	*dataName = *data.DATA_NAME;
	checkAccess("*topColl/*dataName",
		    getDataAccess(*topColl, *dataName), *access,
		    *update);
    }

    # check subcollections
    *topColl = *topColl ++ "/%";
    foreach (*entry in SELECT COLL_NAME WHERE COLL_NAME like *topColl) {
	*coll = *entry.COLL_NAME;
	checkAccess(*coll, getCollAccess(*coll), *access, *update);
	if (*update != 0) {
	    msiSetACL("default", "admin:inherit", "", *coll);
	}

	# check data objects in subcollection
	foreach (*data in SELECT DATA_NAME WHERE COLL_NAME = *coll) {
	    *dataName = *data.DATA_NAME;
	    checkAccess("*coll/*dataName",
			getDataAccess(*coll, *dataName), *access,
			*update);
	}
    }
}

# retrieve the ACLs of a collection
getCollAccess(*coll) {
    *access.own = "";
    foreach (*row in SELECT ORDER(COLL_ACCESS_USER_ID), COLL_ACCESS_NAME WHERE COLL_NAME = *coll) {
	*userId = *row.COLL_ACCESS_USER_ID;
	*name = *row.COLL_ACCESS_NAME;
	if (*name == "own") {
	    *access.own = *access.own ++ "%" ++ *userId;
	    *access."*userId" = "own";
	} else if (*name == "read object") {
	    *access."*userId" = "read";
	} else if (*name == "modify object") {
	    *access."*userId" = "write";
	}
    }
    if (*access.own != "") {
	msiSubstr(*access.own, "1", "-1", *own);
	*access.own = *own;
    }
    *access;
}

# retrieve the ACLs of a data object
getDataAccess(*coll, *data) {
    *access.own = "";
    foreach (*row in SELECT ORDER(DATA_ACCESS_USER_ID), DATA_ACCESS_NAME WHERE COLL_NAME = *coll AND DATA_NAME = *data) {
	*userId = *row.DATA_ACCESS_USER_ID;
	*name = *row.DATA_ACCESS_NAME;
	if (*name == "own") {
	    *access.own = *access.own ++ "%" ++ *userId;
	    *access."*userId" = "own";
	} else if (*name == "read object") {
	    *access."*userId" = "read";
	} else if (*name == "modify object") {
	    *access."*userId" = "write";
	}
    }
    if (*access.own != "") {
	msiSubstr(*access.own, "1", "-1", *own);
	*access.own = *own;
    }
    *access;
}

# check ACLs
checkAccess(*path, *oldAccess, *newAccess, *update) {
    if (*oldAccess.own != *newAccess.own) {
	*own = *oldAccess.own;
	if (*own != "") {
	    msiString2StrArray(*own, *owners);
	    *own = "";
	    foreach (*owner in *owners) {
		foreach (*user in SELECT USER_NAME WHERE USER_ID = *owner) {
		    *own = *own ++ "," ++ *user.USER_NAME;
		    break;
		}
	    }
	    if (*own != "") {
		msiSubstr(*own, "1", "-1", *own);
	    }
	}
	msiString2StrArray(*newAccess.own, *owners);
	foreach (*owner in *owners) {
	    *newOwn = *owner;
	    *oldAccess."*newOwn" = "";
	    foreach (*user in SELECT USER_NAME WHERE USER_ID = *newOwn) {
		*newOwn = *user.USER_NAME;
		break;
	    }
	}
	if (*own != *newOwn) {
	    writeLine("stdout", "*path: owner *own should be *newOwn");

	    if (*update) {
		# add new owner
		msiSetACL("default", "admin:own", *newOwn, *path);
		# remove old access
		foreach (*key in *oldAccess) {
		    if (*key != "own" && *oldAccess."*key" != "") {
			foreach (*user in SELECT USER_NAME WHERE USER_ID = *key) {
			    msiSetACL("default", "admin:null", *user.USER_NAME, *path);
			    break;
			}
		    }
		}
		# add new access
		foreach (*key in *newAccess) {
		    if (*key != "own") {
			foreach (*user in SELECT USER_NAME WHERE USER_ID = *key) {
			    msiSetACL("default", "admin:" ++ *newAccess."*key", *user.USER_NAME, *path);
			    break;
			}
		    }
		}
		writeLine("stdout", "    ...fixed");
	    }
	}
    }
}

input *update=0
output ruleExecOut
