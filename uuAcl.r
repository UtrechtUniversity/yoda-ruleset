# \file	     uuAcl.r
# \brief     Functions to work with ACL's as lists of tuples
# \author    Paul Frederiks
# \copyright Copyright (c) 2017 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief uuacl a datatype to represent an ACL consisting of a tuple with two integers.
#        the first should be a user or group ID, the second an access type as found in COl_ACCESS_TYPE or DATA_ACCESS_TYPE
#
data uuacl =
	| uuacl : int * int -> uuacl

# \brief Find the user name and access level belonging to an uuacl.
#
# \param[in] acl          an uuacl
# \param[out] userName    the username of the user or group belonging to the id
# \param[out] accessLevel One of 'own', 'write', 'read' or 'null'. These are
#                         converted to access types again during a msiSetACL call.
#                         There are a few other access types available in the
#                         irods token table, but they aren't included in either
#                         the icommands or microservices.
#
uuAclToStrings(*acl, *userName, *accessLevel) {
	*userName = "";
	*accessLevel = "";
	uuacl(*userId, *accessType) = *acl;
	foreach(*row in SELECT USER_NAME WHERE USER_ID = "*userId") {
		*userName = *row.USER_NAME;
	}

	if (*accessType > 1120) {
		*accessLevel = 'own'; # 1200
	} else if (*accessType > 1050) {
		*accessLevel = 'write'; # 1120
	} else if (*accessType > 1000) {
		*accessLevel = 'read'; # 1050
	} else {
		*accessLevel = 'null'; # 1000
	}
}

# \brief Generate a list of uuacl's of a collection.
#
# \param[in]  collName name (path) of collection
# \param[out] aclList  list of uuacl's
#
uuAclListOfColl(*collName, *aclList) {
	*aclList = list();
	# The COLL_ACCESS_USER_ID's are sorted high to low but consing will reverse that order
	foreach(*row in SELECT ORDER_DESC(COLL_ACCESS_USER_ID), COLL_ACCESS_TYPE WHERE COLL_NAME = *collName) {
		*acl = uuacl(int(*row.COLL_ACCESS_USER_ID), int(*row.COLL_ACCESS_TYPE));
		*aclList = cons(*acl, *aclList);
	}
}

# \brief Generate a list of uuacl's of a data object.
#
# \param[in] path      data object
# \param[out] aclList  list of uuacl's
#
uuAclListOfDataObj(*path, *aclList) {
	uuChopPath(*path, *collName, *dataName);
	*aclList = list();
	# The DATA_ACCESS_USER_ID's are sorted high to low but consing will reverse that order
	foreach(*row in SELECT ORDER_DESC(DATA_ACCESS_USER_ID), DATA_ACCESS_TYPE WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
		*acl = uuacl(int(*row.DATA_ACCESS_USER_ID), int(*row.DATA_ACCESS_TYPE));
		*aclList = cons(*acl, *aclList);
	}
}

# \brief Generate a list consisting of the set difference (see set theory) between two lists of uuacl's.
#
# \param[in] aclListA   set A
# \param[in] aclListB   set B
# \param[in] idOnly     if true, only check for userId equivalence and ignore accessType. This is useful when determining ACL's to remove.
# \returnvalue set difference of A \ B
#
uuAclListSetDiff(*aclListA, *aclListB, *idOnly) {
	*setDiff = list();
	foreach(*aclA in *aclListA) {
		uuacl(*userIdA, *accessTypeA) = *aclA;
		*foundMatch = false;
		foreach(*aclB in *aclListB) {
			uuacl(*userIdB, *accessTypeB) = *aclB;
			if (*userIdA < *userIdB) {
				# This algorithm takes advantage of the fact that the uuacl lists are sorted low to high.
				break;
			}
			# match on userId and if idOnly is false, match on accessType too
			if (*userIdA == *userIdB && (*idOnly || *accessTypeA == *accessTypeB)) {
					*foundMatch = true;
					break;
			}
		}
		if (!*foundMatch) {
			*setDiff = cons(*aclA, *setDiff);
		}
	}
	*setDiff;
}

# \brief Enforce the ACL's of the group collection on a child path.
#
# \param[in] path	     Path to apply group ACL's to
#
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

		#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: aclList -> *aclList");
		uuAclListOfColl("/*rodsZone/home/*groupName", *groupAclList);
		#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: groupAclList -> *groupAclList");
		*aclsToRemove = uuAclListSetDiff(*aclList, *groupAclList, true);
		#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: aclsToRemove -> *aclsToRemove");
		*aclsToAdd = uuAclListSetDiff(*groupAclList, *aclList, false);
		#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: aclsToAdd -> *aclsToAdd");

		*recurse = if *objType == "-c" then "recursive" else "default"

		foreach(*acl in *aclsToAdd) {
			uuAclToStrings(*acl, *userName, *accessLevel);
			#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: Setting ACL *accessLevel *userName *path");
			msiSetACL(*recurse, *accessLevel, *userName, *path);
		}

		foreach(*acl in *aclsToRemove) {
				uuAclToStrings(*acl, *userName, *accessLevel);
				#DEBUG writeLine("serverLog", "uuEnforceGroupAcl: Removing ACL *accessLevel *userName *path");
				msiSetACL(*recurse, "null", *userName, *path);
		}
}
