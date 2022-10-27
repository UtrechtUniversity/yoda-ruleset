# \file      uuSudoPolicies.r
# \brief     Sudo microservices policies.
# \author    Chris Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Sudo policies {{{

# The preproc rules for sudo actions should only be used for checking whether a
# user is allowed to perform an action.
# Preproc rules should never issue Sudo actions of their own.
# Instead, put any additional actions that may need to be taken with a certain
# sudo action in a postproc rule, which is guaranteed to be executed on
# succesful completion of the sudo action.
#
# There are currently three implementations of the preproc set of sudo policy
# rules, all listed in this rule file.
# In order, these preproc rules:
#
# - Allow only rodsadmin to perform actions
# - Allow actions only when permitted by Group Manager policy rules
# - Allow actions only when permitted by User Settings policy rules
# - Deny all sudo actions (and cut)
#
# * The GM implementations of pre- and postproc rules in this file call a
#   corresponding rule in uuGroupPolicies.r
#
# The postproc rules work slightly differently:
#
# For each sudo action, there is exactly one postproc rule in this file.
# This rule calls any and all postprocessing rules (using applyAllRules) that
# are defined for that sudo action, with a different naming pattern.
#
# To define your own postproc rule for a sudo action, name it, for example,
# uuPostSudoObjAclSet instead of acPostSudoObjAclSet.

# Implementation 1: Allow access only to rodsadmin. {{{

acPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	writeLine("serverLog", "In acPreSudoUserAdd, user is <*userName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoUserRemove(*userName, *policyKv) {
	writeLine("serverLog", "In acPreSudoUserRemove, user is <*userName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	writeLine("serverLog", "In acPreSudoGroupAdd, group is <*groupName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoGroupRemove(*groupName, *policyKv) {
	writeLine("serverLog", "In acPreSudoGroupRemove, group is <*groupName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoGroupMemberAdd(*groupName, *userName, *policyKv) {
	writeLine("serverLog", "In acPreSudoGroupMemberAdd, group is <*groupName>, user is <*userName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoGroupMemberRemove(*groupName, *userName, *policyKv) {
	writeLine("serverLog", "In acPreSudoGroupMemberRemove, group is <*groupName>, user is <*userName>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	writeLine("serverLog", "In acPreSudoObjAclSet, recursive is <*recursive>, access level is <*accessLevel>, other name is <*otherName>, object path is <*objPath>, actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	writeLine("serverLog", "In acPreSudoObjMetaSet, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	writeLine("serverLog", "In acPreSudoObjMetaAdd, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

acPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {
	writeLine("serverLog", "In acPreSudoObjMetaRemove, objname is <*objName>, objType is <*objType>, attribute is <*attribute>, value is <*value>, unit is <*unit> actor is <$userNameClient#$rodsZoneClient>");
	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") { fail; }
}

# }}}
# Implementation 2: Group manager policy implementations. {{{

acPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	uuGroupPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv);
}

acPreSudoUserRemove(*userName, *policyKv) {
	uuGroupPreSudoUserRemove(*userName, *policyKv);
}

acPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	uuGroupPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv);
}

acPreSudoGroupRemove(*groupName, *policyKv) {
	uuGroupPreSudoGroupRemove(*groupName, *policyKv);
}

acPreSudoGroupMemberAdd(*groupName, *userName, *policyKv) {
	uuGroupPreSudoGroupMemberAdd(*groupName, *userName, *policyKv);
}

acPreSudoGroupMemberRemove(*groupName, *userName, *policyKv) {
	uuGroupPreSudoGroupMemberRemove(*groupName, *userName, *policyKv);
}

acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	uuGroupPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
}

# Only define Group Manager rules for meta operations on User / Group objects.

acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-u") {
		uuGroupPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv);
	}
}

acPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-u") {
		uuGroupPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv);
	}
}

acPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-u") {
		uuGroupPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv);
	}
}

# }}}
# Implementation 3: User settings policy implementations. {{{
# Only define User Settings rules for meta operations on User / Group objects.

acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-u") {
		uuUserPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv);
	}
}

acPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {
	ON (*objType == "-u") {
		uuUserPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv);
	}
}

# }}}
# Implementation 4: Deny everything and cut. {{{

acPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) { cut; fail; }
acPreSudoUserRemove(*userName, *policyKv) { cut; fail; }
acPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) { cut; fail; }
acPreSudoGroupRemove(*groupName, *policyKv) { cut; fail; }
acPreSudoGroupMemberAdd(*groupName, *userName, *policyKv) { cut; fail; }
acPreSudoGroupMemberRemove(*groupName, *userName, *policyKv) { cut; fail; }
acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) { cut; fail; }
acPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) { cut; fail; }
acPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) { cut; fail; }
acPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) { cut; fail; }

# }}}
# Postprocessing rules. {{{

# Call all postproc implementations.

# Note: Postproc rule implementations must NOT alter their parameters, as
# changes will be visible to any other implementations of the postproc rule
# that are called next.

acPostSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	applyAllRules(uuPostSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv), "0", "0");
}

acPostSudoUserRemove(*userName, *policyKv) {
	applyAllRules(uuPostSudoUserRemove(*userName, *policyKv), "0", "0");
}

acPostSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {
	applyAllRules(uuPostSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv), "0", "0");
}

acPostSudoGroupRemove(*groupName, *policyKv) {
	applyAllRules(uuPostSudoGroupRemove(*groupName, *policyKv), "0", "0");
}

acPostSudoGroupMemberAdd(*groupName, *userName, *policyKv) {
	applyAllRules(uuPostSudoGroupMemberAdd(*groupName, *userName, *policyKv), "0", "0");
}

acPostSudoGroupMemberRemove(*groupName, *userName, *policyKv) {
	applyAllRules(uuPostSudoGroupMemberRemove(*groupName, *userName, *policyKv), "0", "0");
}

acPostSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	applyAllRules(uuPostSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv), "0", "0");
}

acPostSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	applyAllRules(uuPostSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv), "0", "0");
}

acPostSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	applyAllRules(uuPostSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv), "0", "0");
}

acPostSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {
	applyAllRules(uuPostSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv), "0", "0");
}

# }}}
# }}}
