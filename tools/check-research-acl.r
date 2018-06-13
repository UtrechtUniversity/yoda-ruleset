#!/usr/bin/irule -F
#
# Report, and optionally fix, bad ACLs for research collections
#
# usage: check-research-acl
#        check-research-acl "*update=1"
#
checkResearchACL() {
    foreach (*row in SELECT COLL_NAME WHERE COLL_NAME like '/$rodsZoneClient/home/research-%') {
	*topColl = *row.COLL_NAME;
	if (*topColl not like "/$rodsZoneClient/home/research\*/\*") {
	    # get access rights of research collection
	    *access = getCollAccess(*topColl);

	    # check data objects in research collection
	    foreach (*data in SELECT DATA_NAME WHERE COLL_NAME = *topColl) {
		*dataName = *data.DATA_NAME;
		updateAccess("*topColl/*dataName",
			     getDataAccess(*topColl, *dataName), *access,
			     *update);
	    }

	    # check subcollections
	    *topColl = *topColl ++ "/%";
	    foreach (*entry in SELECT COLL_NAME WHERE COLL_NAME like *topColl) {
		*coll = *entry.COLL_NAME;
		updateAccess(*coll, getCollAccess(*coll), *access, *update);
		if (*update != 0) {
		    msiSetACL("default", "inherit", "", *coll);
		}

		# check data objects in subcollection
		foreach (*data in SELECT DATA_NAME WHERE COLL_NAME = *coll) {
		    *dataName = *data.DATA_NAME;
		    updateAccess("*coll/*dataName",
				 getDataAccess(*coll, *dataName), *access,
				 *update);
		}
	    }
	}
    }
}

# retrieve the ACLs of a collection
getCollAccess(*coll) {
    *access.own = "";
    foreach (*row in SELECT COLL_ACCESS_NAME, COLL_ACCESS_USER_ID WHERE COLL_NAME = *coll) {
	*name = *row.COLL_ACCESS_NAME;
	*userId = *row.COLL_ACCESS_USER_ID;
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
    foreach (*row in SELECT DATA_ACCESS_NAME, DATA_ACCESS_USER_ID WHERE COLL_NAME = *coll AND DATA_NAME = *data) {
	*name = *row.DATA_ACCESS_NAME;
	*userId = *row.DATA_ACCESS_USER_ID;
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

# update ACLs
updateAccess(*path, *oldAccess, *newAccess, *update) {
    if (*oldAccess.own != *newAccess.own) {
	*own = *oldAccess.own;
	if (*own != "") {
	    msiString2StrArray(*own, *owners);
	    *own = "";
	    foreach (*owner in *owners) {
		foreach (*user in SELECT USER_NAME WHERE USER_ID = *owner) {
		    *owner = *user.USER_NAME;
		    break;
		}
		*own = *own ++ "," ++ *owner;
	    }
	    msiSubstr(*own, "1", "-1", *own);
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
	writeLine("stdout", "*path: owner *own should be *newOwn");

	if (*update) {
	    # add new owner
	    msiSetACL("default", "own", *newOwn, *path);
	    # remove old access
	    foreach (*key in *oldAccess) {
		if (*key != "own" && *oldAccess."*key" != "") {
		    foreach (*user in SELECT USER_NAME WHERE USER_ID = *key) {
			msiSetACL("default", "null", *user.USER_NAME, *path);
			break;
		    }
		}
	    }
	    # add new access
	    foreach (*key in *newAccess) {
		if (*key != "own") {
		    foreach (*user in SELECT USER_NAME WHERE USER_ID = *key) {
			msiSetACL("default", *newAccess."*key", *user.USER_NAME, *path);
			break;
		    }
		}
	    }
	    writeLine("stdout", "    ...fixed");
	}
    }
}

input *update=0
output ruleExecOut
