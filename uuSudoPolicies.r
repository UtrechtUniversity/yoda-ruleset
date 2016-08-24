# \file
# \brief     Sudo microservices policies.
# \author    Chris Smeele
# \copyright Copyright (c) 2016, Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

# Preprocessing rules. {{{

acPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoUserAdd, user is <*userName>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	if (*initialAttr != "") { fail; }

	# If the actor can add the user to a group, allow him to create the user.
	uuGroupPolicyCanGroupUserAdd(
		$userNameClient,
		*policyKv."forGroup",
		*userName,
		*allowed, *reason
	);
	if (*allowed == 1) {
		succeed;
	}

	fail;
}

acPreSudoUserRemove(*userName, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoUserRemove, user is <*userName>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	# Do not allow this.

	fail;
}

acPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoGroupAdd, group is <*groupName>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	if (*initialAttr != "manager" || *initialValue != $userNameClient) {
		fail;
	}
	uuGroupPolicyCanGroupAdd(
		$userNameClient,
		*groupName,
		*policyKv."category",
		*policyKv."subcategory",
		*policyKv."description",
		*allowed, *reason
	);
	if (*allowed == 1) {
		succeed;
	}
	fail;
}

acPreSudoGroupRemove(*groupName, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoGroupRemove, group is <*groupName>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	uuGroupPolicyCanGroupRemove($userNameClient, *groupName, *allowed, *reason);
	if (*allowed == 1) {
		succeed;
	}
	fail;
}

acPreSudoGroupMemberAdd(*groupName, *userName, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoGroupMemberAdd, group is <*groupName>, user is <*userName>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	uuGroupPolicyCanGroupUserAdd(
		$userNameClient,
		*groupName,
		*userName,
		*allowed, *reason
	);
	if (*allowed == 1) {
		succeed;
	}
	fail;
}

acPreSudoGroupMemberRemove(*groupName, *userName, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoGroupMemberRemove, group is <*groupName>, user is <*userName>, actor is <$userNameClient>");

	uuGroupPolicyCanGroupUserRemove(
		$userNameClient,
		*groupName,
		*userName,
		*allowed, *reason
	);
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { *allowed = 1; }

	if (*allowed == 1) {
		# Make sure we remove the user's role metadata first.
		#errorcode(msiSudoObjMetaRemove(*groupName, "-u", 0, "manager", *userName, "", ""));
		uuGroupUserChangeRole(*groupName, *userName, "user", *status, *msg);
		if (*status == 0) {
			succeed;
		}
	}

	fail;
}

acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoObjAclSet, recursive is <*recursive>, access level is <*accessLevel>, other name is <*otherName>, object path is <*objPath>, actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	fail;
}

acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoObjMetaSet, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			if (# We do not use / allow the unit field here.
				*unit == ""
			) {
				uuGroupPolicyCanGroupModify($userNameClient, *objName, *attribute, *value, *allowed, *reason);
				if (*allowed == 1) {
					succeed;
				}
			}
		}
	}
	fail;
}

acPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoObjMetaAdd, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			if (*attribute == "manager" && *unit == "") {
				uuGroupPolicyCanAddManager($userNameClient, *objName, *value, *allowed, *reason);
				if (*allowed == 1) {
					succeed;
				}
			}
		}
	}
	fail;
}

acPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {
	cut;
	writeLine("serverLog", "In acPreSudoObjMetaRemove, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient>");
	uuGetUserType($userNameClient, *userType);
	if (*userType == "rodsadmin") { succeed; }

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			if (*attribute == "manager" && *unit == "") {
				uuGroupPolicyCanRemoveManager($userNameClient, *objName, *value, *allowed, *reason);
				if (*allowed == 1) {
					succeed;
				}
			}
		}
	}
	fail;
}

# }}}
# Postprocessing rules. {{{

acPostSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) { }

acPostSudoUserRemove(*userName, *policyKv) { }

acPostSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	writeLine("serverLog", "In acPostSudoGroupAdd, group is <*groupName>, actor is <$userNameClient>");
	# Note: These should not fail.
	errorcode(msiSudoGroupMemberAdd(*groupName, $userNameClient, ""));
	errorcode(msiSudoObjMetaSet(*groupName, "-u", "category",      *policyKv."category",    "", ""));
	errorcode(msiSudoObjMetaSet(*groupName, "-u", "subcategory",   *policyKv."subcategory", "", ""));

	*description = if *policyKv."description" != "" then *policyKv."description" else ".";
	errorcode(msiSudoObjMetaSet(*groupName, "-u", "description",   *description, "", ""));
}

acPostSudoGroupRemove(*groupName, *policyKv) { }

acPostSudoGroupMemberAdd(*groupName, *userName, *policyKv) { }

acPostSudoGroupMemberRemove(*groupName, *userName, *policyKv) { }

acPostSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) { }

acPostSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) { }

acPostSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) { }

acPostSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) { }

# }}}
