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
		updateAccess("/*topColl/*data",
			     getDataAccess(*topColl, *data.DATA_NAME),
			     *access, *update);
	    }

	    # check subcollections
	    *topColl = *topColl ++ "/%";
	    foreach (*entry in SELECT COLL_NAME WHERE COLL_NAME like *topColl) {
		*coll = *entry.COLL_NAME;
		updateAccess(*coll, getCollAccess(*coll), *access, *update);

		# check data objects in subcollection
		foreach (*data in SELECT DATA_NAME WHERE COLL_NAME = *coll) {
		    updateAccess("/*coll/*data",
				 getDataAccess(*coll, *data.DATA_NAME),
				 *access, *update);
		}
	    }
	}
    }
}

# retrieve the ACLs of a collection
getCollAccess(*coll) {
    msiString2KeyValPair("", *access);
    foreach (*row in SELECT COLL_ACCESS_NAME, COLL_ACCESS_USER_ID WHERE COLL_NAME = *coll) {
	*name = *row.COLL_ACCESS_NAME;
	*userId = *row.COLL_ACCESS_USER_ID;
	foreach (*user in SELECT USER_NAME WHERE USER_ID = *userId) {
	    *userName = *user.USER_NAME;
	}
	if (*name == "own") {
	    *access.own = *userName;
	    *access."*userName" = "own";
	} else if (*name == "read object") {
	    *access."*userName" = "read";
	} else if (*name == "modify object") {
	    *access."*userName" = "write";
	}
    }
    *access;
}

# retrieve the ACLs of a data object
getDataAccess(*coll, *data) {
    msiString2KeyValPair("", *access);
    foreach (*row in SELECT DATA_ACCESS_NAME, DATA_ACCESS_USER_ID WHERE COLL_NAME = *coll AND DATA_NAME = *data) {
	*name = *row.DATA_ACCESS_NAME;
	*userId = *row.DATA_ACCESS_USER_ID;
	foreach (*user in SELECT USER_NAME WHERE USER_ID = *userId) {
	    *userName = *user.USER_NAME;
	}
	if (*name == "own") {
	    *access.own = *userName;
	    *access."*userName" = "own";
	} else if (*name == "read object") {
	    *access."*userName" = "read";
	} else if (*name == "modify object") {
	    *access."*userName" = "write";
	}
    }
    *access;
}

# update ACLs
updateAccess(*path, *oldAccess, *newAccess, *update) {
    if (*oldAccess.own != *newAccess.own) {
	*own = *oldAccess.own;
	*newOwn = *newAccess.own;
	writeLine("stdout", "*path: owner *own should be *newOwn");

	if (*update) {
	    # add new owner
	    msiSetACL("default", "own", *newAccess.own, *path);
	    # remove old access 
	    foreach (*key in *oldAccess) {
		if (*key != "own") {
		    msiSetACL("default", "null", *key, *path);
		}
	    }
	    # add new access
	    foreach (*key in *newAccess) {
		if (*key != "own") {
		    msiSetACL("default", *newAccess."*key", *key, *path);
		}
	    }
	    writeLine("stdout", "    ...fixed");
	}
    }
}

input *update=0
output ruleExecOut
