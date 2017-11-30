data uuacl = 
	| uuacl : int * int -> uuacl

uuids(*aclList) {
	*ids = list();
	foreach(*acl in *aclList) {
		uuacl(*userId, *accessType) = *acl;
		*ids = cons(*userId, *ids);
	}
	*ids;
}

uuAclEqual(*aclA, *aclB) {
	uuacl(*userIdA, *accessTypeA) = *aclA;
	uuacl(*userIdB, *accessTypeB) = *aclB;
	*equality = false;
	if (*userIdA == *userIdB && *accessTypeA == *accessTypeB) {
		*equality = true;
	}
	*equality;
}
	

uuAclToStrings(*acl, *userName, *accessLevel) {
	*userName = "";
	*accessLevel = "";
	uuacl(*userId, *accessType) = *acl;
	foreach(*row in SELECT USER_NAME WHERE USER_ID = "*userId") {
		*userName = *row.USER_NAME;
	}

	if (*accessType > 1120) {
		*accessLevel = 'own';
	} else if (*accessType > 1050) {
		*accessLevel = 'write';
	} else if (*accessType > 1000) {
		*accessLevel = 'read';
	} else {
		*accessLevel = 'null';
	}
	
}

uuAclListOfPath(*path, *aclList) {
	msiGetObjType(*path, *objType);
	if (*objType == "-c") {
		uuAclListOfColl(*path, *aclList);
	} else {
		uuAclListOfDataObj(*path, *aclList);
	}
}

uuAclListOfColl(*collName, *aclList) {
	*aclList = list();
	foreach(*row in SELECT ORDER_DESC(COLL_ACCESS_USER_ID), COLL_ACCESS_TYPE WHERE COLL_NAME = *collName) {
		*acl = uuacl(int(*row.COLL_ACCESS_USER_ID), int(*row.COLL_ACCESS_TYPE));
		*aclList = cons(*acl, *aclList);
	}
}

uuAclListOfDataObj(*path, *aclList) {
	*aclList = list();
	uuChopPath(*path, *collName, *dataName);
	foreach(*row in SELECT ORDER_DESC(DATA_ACCESS_USER_ID), DATA_ACCESS_TYPE WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
		*acl = uuacl(int(*row.DATA_ACCESS_USER_ID), int(*row.DATA_ACCESS_TYPE));
		*aclList = cons(*acl, *aclList);
	}
}


uuAclListSetDiff(*aclListA, *aclListB, *setDiff) {
	*setDiff = list();
	foreach(*aclA in *aclListA) {
		uuacl(*userIdA, *accessTypeA) = *aclA;
		*foundMatch = false;
		foreach(*aclB in *aclListB) {	
			uuacl(*userIdB, *accessTypeB) = *aclB;
			if (*userIdA < *userIdB) {
				break;
			}
			if (*userIdA == *userIdB && *accessTypeA == *accessTypeB) {
				*foundMatch = true;
				break;
			}
		}
		if (!*foundMatch) {
			*setDiff = cons(*aclA, *setDiff);
		}
	}
}

# \brief uuEnforceGroupAcl   Enforce the ACL's of the group collection on a child path
# \param[in] path	     Path to apply group ACL's to
uuEnforceGroupAcl(*path) {
		*pathElems = split(*path, '/');
		if (elem(*pathElems, 1) != "home") {
			failmsg(-1, "*path not in a group home collection");
		}

		*groupName = elem(*pathElems, 2);
		*rodsZone =  elem(*pathElems, 0);

		msiGetObjType(*path, *objType);

		if (*objType == "-c") {
			uuAclListOfColl(*path, *aclList);
		} else {
			uuAclListOfDataObj(*path, *aclList);
		}

		#DEBUG writeLine("serverLog", "aclList: *aclList");
		uuAclListOfColl("/*rodsZone/home/*groupName", *groupAclList);
		#DEBUG writeLine("serverLog", "groupAclList: *groupAclList");
		uuAclListSetDiff(*aclList, *groupAclList, *aclsToRemove);
		#DEBUG writeLine("serverLog", "aclsToRemove: *aclsToRemove");
		uuAclListSetDiff(*groupAclList, *aclList, *aclsToAdd);
		#DEBUG writeLine("serverLog", "aclsToAdd: *aclsToAdd");
		*idsToAdd = uuids(*aclsToAdd);

		*recurse = if *objType == "-c" then "recursive" else "default"
		 
		foreach(*acl in *aclsToAdd) {
			uuAclToStrings(*acl, *userName, *accessLevel);
			#DEBUG writeLine("serverLog", "acPostProcForObjRename: Setting ACL *accessLevel *userName *path");
			msiSetACL(*recurse, *accessLevel, *userName, *path);
		}
		
		foreach(*acl in *aclsToRemove) {
			uuacl(*userId, *accessType) = *acl;
			if (!uuinlist(*userId, *idsToAdd)) {
				uuAclToStrings(*acl, *userName, *accessLevel);
				#DEBUG writeLine("serverLog", "acPostProcForObjRename: Removing ACL *accessLevel *userName *path");
				msiSetACL(*recurse, "null", *userName, *path);	
			}
		}
}
