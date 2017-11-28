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
	*aclList = list();
	msiGetObjType(*path, *objType);
	if (*objType == "-c") {
		foreach(*row in SELECT ORDER_DESC(COLL_ACCESS_USER_ID), COLL_ACCESS_TYPE WHERE COLL_NAME = *path) {
			*acl = uuacl(int(*row.COLL_ACCESS_USER_ID), int(*row.COLL_ACCESS_TYPE));
			*aclList = cons(*acl, *aclList);
		}
	} else {
		uuChopPath(*path, *collName, *dataName);
		foreach(*row in SELECT ORDER_DESC(DATA_ACCESS_USER_ID), DATA_ACCESS_TYPE WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
			*acl = uuacl(int(*row.DATA_ACCESS_USER_ID), int(*row.DATA_ACCESS_TYPE));
			*aclList = cons(*acl, *aclList);
		}
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
