# \file
# \brief     Functions for group management and group queries.
# \author    Ton Smeele
# \author    Chris Smeele
# \copyright Copyright (c) 2015 - 2017 Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

#test() {
#	*user = "ton#nluu1ot";
#   *group = "groupyoda";
#	uuGroupUserExists(*group, *user, *membership);
#	writeLine("stdout","*user membership of group *group : *membership");
#	uuGroupMemberships(*user, *groups);
#	foreach (*grp in *groups){
#		writeLine("stdout","grp = *grp");
#	}
#}

# \brief Get the user type for a given user
#
# \param[in]  user     name of the irods user(#zone)
# \param[out] type     usertype e.g. rodsuser, rodsgroup, rodsadmin
#
uuGetUserType(*user, *userType) {
	*userType = "";
	uuGetUserAndZone(*user, *userName, *userZone);
	foreach (
		*row in
		SELECT USER_TYPE
		WHERE  USER_NAME = '*userName'
		AND    USER_ZONE = '*userZone'
	) {
		*userType = *row."USER_TYPE";
		break;
	}
}

# \brief Extract username and zone in separate fields.
#
# \param[in] user       name of the irods user
#                       username can optionally include zone ('user#zone')
#                       default is to use the local zone
# \param[out] userName  name of user exclusing zone information
# \param[out] userZone  name of the zone of the user
#
uuGetUserAndZone(*user,*userName,*userZone) {
	*userAndZone = split(*user, "#");
	*userName = elem(*userAndZone,0);
	if (size(*userAndZone) > 1) {
		*userZone = elem(*userAndZone,1);
	} else {
		*userZone = $rodsZoneClient;
	}
}

# \brief Check if a group category exists.
#
# \param[in]  categoryName
# \param[out] exists
#
uuGroupCategoryExists(*categoryName, *exists) {
	*exists = false;
	foreach (
		*row in
		SELECT META_USER_ATTR_VALUE
		WHERE  USER_TYPE            = 'rodsgroup'
		  AND  META_USER_ATTR_NAME  = 'category'
		  AND  META_USER_ATTR_VALUE = '*categoryName'
	) {
		*exists = true;
	}
}

# \brief Check if a rodsgroup with the given name exists.
#
# \param[in]  groupName
# \param[out] exists
#
uuGroupExists(*groupName, *exists) {
	*exists = false;
	foreach (
		*row in
		SELECT USER_GROUP_NAME, USER_TYPE
		WHERE  USER_GROUP_NAME = '*groupName'
		  AND  USER_TYPE       = 'rodsgroup'
	) {
		*exists = true;
	}
}

# \brief Check if a rodsuser or rodsadmin with the given name exists.
#
# \param[in]  userName	 username(#zone)
# \param[out] exists
#
uuUserExists(*user, *exists) {
	*exists = false;
	uuGetUserAndZone(*user, *userName, *userZone);
	foreach (
		*row in
		SELECT USER_NAME, USER_TYPE
		WHERE  USER_NAME = '*userName'
		  AND  USER_ZONE = '*userZone'
		  AND  USER_TYPE = 'rodsuser'
	) {
		*exists = true;
		break;
	}
	if (!*exists) {
		foreach (
			*row in
			SELECT USER_NAME, USER_TYPE
			WHERE  USER_NAME = '*userName'
			  AND  USER_ZONE = '*userZone'
			  AND  USER_TYPE = 'rodsadmin'
		) {
			*exists = true;
			break;
		}
	}
}

# \brief Check if a user is a member of the given group.
#
# \param[in] group        name of the irods group
# \param[in] user         name of the irods user
#                         username can optionally include zone ('user#zone')
#                         default is to use the local zone
# \param[out] membership  true if user is a member of this group
#
uuGroupUserExists(*group, *user, *membership) {
	*membership = false;
	uuGetUserAndZone(*user,*userName,*userZone);
	foreach (*row in SELECT USER_NAME,USER_ZONE WHERE USER_GROUP_NAME=*group) {
		msiGetValByKey(*row, "USER_NAME", *member);
		msiGetValByKey(*row, "USER_ZONE", *memberZone);
		if ((*member == *userName) && (*memberZone == *userZone)) {
			*membership = true;
		}
	}
}

# \brief Check if a name is available in the iRODS username namespace.
#
# The username namespace includes names of the following user types:
#
# - rodsgroup
# - rodsadmin
# - rodsuser
# - domainadmin
# - groupadmin
# - storageadmin
# - rodscurators
#
# \param[in]  name
# \param[out] available
# \param[out] existingType set to the USER_TYPE if the name is unavailable
#
uuUserNameIsAvailable(*name, *available, *existingType) {
	*available    = true;
	*existingType = ".";

	foreach (
		*row in
		SELECT USER_NAME, USER_TYPE
		WHERE  USER_NAME = '*name'
	) {
		*available    = false;
		*existingType = *row."USER_TYPE";
		break;
	}
}

# \brief List all groups the user belongs to.
#
# \param[in] user     name of the irods user
#                     username can optionally include zone ('user#zone')
#                     default is to use the local zone
# \param[out] groups  irods list of groupnames
#
uuGroupMemberships(*user, *groupList) {
	uuGetUserAndZone(*user,*userName,*userZone);
	*groups = "";
	foreach (*row in SELECT USER_GROUP_NAME, USER_GROUP_ID 
				WHERE USER_NAME = '*userName' AND USER_ZONE = '*userZone') {
		msiGetValByKey(*row,"USER_GROUP_NAME",*group);
		# workasround needed: iRODS returns username also as a group !! 
		# TODO: -> no it doesn't, add USER_TYPE to query.
		if (*group != *userName) {
			*groups = "*groups:*group";
		}
	}
	*groups = triml(*groups,":");
	*groupList = split(*groups, ":");
}

# \brief Get a list of all rodsgroups.
#
# \param[out] groupList list of groupnames
#
uuGetAllGroups(*groupList) {
	*groups = "";
	foreach (
		*row in
		SELECT USER_GROUP_NAME
		WHERE  USER_TYPE = 'rodsgroup'
	) {
		*groupName = *row."USER_GROUP_NAME";

		if (strlen(*groups) > 0) {
			*groups = "*groups,*groupName";
		} else {
			*groups = *groupName;
		}
	}
	*groupList = split(*groups, ",");
}

# \brief Get a list of group subcategories for the given category.
#
# \param[in]  category      a category name
# \param[out] subcategories a list of subcategory names
#
uuGroupGetSubcategories(*category, *subcategories) {

	*subcategoriesString = "";
	foreach (
		# Get groups that belong to this category...
		*categoryGroupRow in
		SELECT USER_GROUP_NAME
		WHERE  USER_TYPE            = 'rodsgroup'
		AND    META_USER_ATTR_NAME  = 'category'
		AND    META_USER_ATTR_VALUE = '*category'
	) {
		*groupName = *categoryGroupRow."USER_GROUP_NAME";
		foreach (
			# ... and collect their subcategories.
			*subcategoryRow in
			SELECT META_USER_ATTR_VALUE
			WHERE  USER_TYPE           = 'rodsgroup'
			AND    USER_GROUP_NAME     = '*groupName'
			AND    META_USER_ATTR_NAME = 'subcategory'
		) {
			*subcategoryName = *subcategoryRow."META_USER_ATTR_VALUE";
			if (!(
				   (*subcategoriesString == *subcategoryName)
				|| (*subcategoriesString like "*,*subcategoryName")
				|| (*subcategoriesString like   "*subcategoryName,*")
				|| (*subcategoriesString like "*,*subcategoryName,*")
			)) {
				if (strlen(*subcategoriesString) > 0) {
					*subcategoriesString = "*subcategoriesString,*subcategoryName";
				} else {
					*subcategoriesString = *subcategoryName;
				}
			}
		}
	}
	*subcategories = split(*subcategoriesString, ",");
}

# \brief Get a list of group categories.
#
# \param[out] categories a list of category names
#
uuGroupGetCategories(*categories) {
	*categoriesString = "";
	foreach (
		*category in
		SELECT META_USER_ATTR_VALUE
		WHERE  USER_TYPE           = 'rodsgroup'
		  AND  META_USER_ATTR_NAME = 'category'
	) {
		*categoriesString = "*categoriesString," ++ *category."META_USER_ATTR_VALUE";
	}
	*categories = split(*categoriesString, ",");
}

# \brief Get a group's category and subcategory.
#
# \param[in]  groupName
# \param[out] category
# \param[out] subcategory
#
uuGroupGetCategory(*groupName, *category, *subcategory) {
	*category    = "";
	*subcategory = "";
	foreach (
		*item in
		SELECT META_USER_ATTR_NAME, META_USER_ATTR_VALUE
		WHERE  USER_GROUP_NAME = '*groupName'
		  AND  META_USER_ATTR_NAME LIKE '%category'
	) {
		if (*item."META_USER_ATTR_NAME" == 'category') {
			*category = *item."META_USER_ATTR_VALUE";
		} else if (*item."META_USER_ATTR_NAME" == 'subcategory') {
			*subcategory = *item."META_USER_ATTR_VALUE";
		}
	}
}

# \brief Get a group's desription.
#
# \param[in]  groupName
# \param[out] decsription
#
uuGroupGetDescription(*groupName, *description) {
	*description = "";
	foreach (
		*item in
		SELECT META_USER_ATTR_VALUE
		WHERE  USER_GROUP_NAME     = '*groupName'
		  AND  META_USER_ATTR_NAME = 'description'
	) {
		if (*item."META_USER_ATTR_VALUE" != ".") {
			*description = *item."META_USER_ATTR_VALUE";
		}
	}
}

# \brief Get a list of both manager and non-manager members of a group.
#
# This function ignores zone names, this is usually a bad idea.
#
# \deprecated Use uuGroupGetMembers(*groupName, *includeRo, *addTypePrefix, *members) instead
#
# \param[in]  groupName
# \param[out] members a list of user names
#
uuGroupGetMembers(*groupName, *members) {
	uuGroupGetMembers(*groupName, false, false, *m);
	*members = list();
	foreach (*member in *m) {
		# Throw away the zone name.
		uuChop(*member, *name, *_, "#", true);
		*members = cons(*name, *members);
	}
}

# \brief Get a list of members of a group.
#
# \param[in]  groupName
# \param[in]  includeRo     whether to include members with read-only access
# \param[in]  addTypePrefix whether to prefix user names with the type of member they are (see below)
# \param[out] members       a list of user names
#
# If addTypePrefix is true, usernames will be prefixed with 'r:', 'n:',
# or 'm:', if they are, respectively, a read-only member, normal
# member, or a manager of the given group.
#
uuGroupGetMembers(*groupName, *includeRo, *addTypePrefix, *members) {

	*members = list();

	uuGroupGetManagers(*groupName, *managers);

	foreach (*manager in *managers) {
		*members = cons(if *addTypePrefix then "m:*manager" else "*manager", *members);
	}

	foreach (
		*member in
		SELECT USER_NAME,
		       USER_ZONE
		WHERE  USER_GROUP_NAME = '*groupName'
		  AND  USER_TYPE != 'rodsgroup'
	) {
		*name = *member."USER_NAME";
		*zone = *member."USER_ZONE";

		uuListMatches(*members, "(m:)?*name#*zone", *isAlsoManager);
		if (!*isAlsoManager) {
			*members = cons(if *addTypePrefix then "n:*name#*zone" else "*name#*zone", *members);
		}
	}

	if (*includeRo && *groupName like regex ``(research|intake)-.+``) {
		uuChop(*groupName, *_, *groupBaseName, '-', true);
		foreach (
			*member in
			SELECT USER_NAME,
			       USER_ZONE
			WHERE  USER_GROUP_NAME == 'read-*groupBaseName'
			AND    USER_TYPE != 'rodsgroup'
		) {
			*name = *member."USER_NAME";
			*zone = *member."USER_ZONE";

			uuListMatches(*members, "([mn]:)?*name#*zone", *isNonRoMember);
			if (!*isNonRoMember) {
				*members = cons(if *addTypePrefix then "r:*name#*zone" else "*name#*zone", *members);
			}
		}
	}
}

# \brief Get a list of managers for the given group.
#
# \param[in]  groupName
# \param[out] managers
#
uuGroupGetManagers(*groupName, *managers) {
	*managers = list();
	foreach (
		*manager in
		SELECT META_USER_ATTR_VALUE
		WHERE  USER_GROUP_NAME	   = '*groupName'
		  AND  META_USER_ATTR_NAME = 'manager'
	) {
		# For backward compatibility, let zone be $rodsZoneClient if
		# it's not present in metadata.
		uuGetUserAndZone(*manager."META_USER_ATTR_VALUE", *name, *zone);
		*managers = cons("*name#*zone", *managers);
	}
}

# \brief Get a list of all irods users.
#
# \param[out] users a list of user names
#
uuGetUsers(*users) {
	*usersString = "";
	foreach (
		*user in
		SELECT USER_NAME
		WHERE  USER_TYPE = 'rodsuser'
	) {
		*usersString = "*usersString;" ++ *user."USER_NAME";
	}
	foreach (
		*user in
		SELECT USER_NAME
		WHERE  USER_TYPE = 'rodsadmin'
	) {
		*usersString = "*usersString;" ++ *user."USER_NAME";
	}

	*users = split(*usersString, ";");
}

# \brief Find users matching a pattern.
#
# \param[in]  query
# \param[out] users a list of user names
#
uuFindUsers(*query, *users) {
	*usersString = "";
	foreach (
		*user in
		SELECT USER_NAME
		WHERE  USER_TYPE = 'rodsuser'
		  AND  USER_NAME LIKE '%*query%'
	) {
		*usersString = "*usersString;" ++ *user."USER_NAME";
	}
	foreach (
		*user in
		SELECT USER_NAME
		WHERE  USER_TYPE = 'rodsadmin'
		  AND  USER_NAME LIKE '%*query%'
	) {
		*usersString = "*usersString;" ++ *user."USER_NAME";
	}

	*users = split(*usersString, ";");
}

# \brief Check if a user is a member of the given group.
#
# \param[in]  groupName
# \param[in]  userName
# \param[out] isMember
#
uuGroupUserIsMember(*groupName, *userName, *isMember) {
	*isMember = false;
	uuGetUserAndZone(*userName, *name, *zone);

	foreach (
		*row in
		SELECT USER_GROUP_NAME
		WHERE USER_NAME = '*name'
		  AND USER_ZONE = '*zone'
		  AND USER_GROUP_NAME = '*groupName'
	) {
		*isMember = true;
	}
}

# \brief Check if a user is a manager in the given group.
#
# \param[in]  groupName
# \param[in]  userName
# \param[out] isManager
#
uuGroupUserIsManager(*groupName, *userName, *isManager) {
	*isManager = false;

	uuGroupUserIsMember(*groupName, *userName, *isMember);
	if (*isMember) {
		foreach (
			*manager in
			SELECT META_USER_ATTR_VALUE
			WHERE  USER_GROUP_NAME      = '*groupName'
			  AND  META_USER_ATTR_NAME  = 'manager'
			  AND  META_USER_ATTR_VALUE = '*userName'
		) {
			*isManager = true;
		}
	}
}

# Privileged group management functions {{{

# \brief Create a group.
#
# \param[in]  groupName
# \param[out] status  zero on success, non-zero on failure
# \param[out] message a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupAdd(*groupName, *category, *subcategory, *description, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*kv."category"    = *category;
	*kv."subcategory" = *subcategory;
	*kv."description" = *description;

	# Shoot first, ask questions later.
	*status = errorcode(msiSudoGroupAdd(*groupName, "manager", $userNameClient, "", *kv));

	if (*status == 0) {
		*message = "";
	} else {
		# Why didn't you allow me to do that?
		uuGroupPolicyCanGroupAdd(
			$userNameClient,
			*groupName,
			*category,
			*subcategory,
			*description,
			*allowed,
			*reason
		);
		if (*allowed == 0) {
			# We were too impolite.
			*message = *reason;
		} else {
			# There were actually no objections. Something else must
			# have gone wrong.
			# The *message set in the start of this rule is returned.
		}
	}
}

# \brief Modify a group.
#
# \param[in]  groupName
# \param[in]  property  the property to change
# \param[in]  value     the new property value
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupModify(*groupName, *property, *value, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*status = errorcode(msiSudoObjMetaSet(*groupName, "-u", *property, *value, "", ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupModify($userNameClient, *groupName, *property, *value, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Remove a group.
#
# \param[in]  groupName
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupRemove(*groupName, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*status = errorcode(msiSudoGroupRemove(*groupName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupRemove($userNameClient, *groupName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Add a user to a group.
#
# \param[in]  groupName
# \param[in]  userName  the user to add to the group
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserAdd(*groupName, *userName, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	uuUserExists(*userName, *exists);
	if (!*exists) {
		*kv."forGroup" = *groupName;
		*status = errorcode(msiSudoUserAdd(*userName, "", "", "", *kv));
		if (*status != 0) {
			uuGroupPolicyCanGroupUserAdd($userNameClient, *groupName, *userName, *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed; # Return here (don't fail as that would ruin the status and error message).
		}
	}
	# User exists, now add them to the group.
	*status = errorcode(msiSudoGroupMemberAdd(*groupName, *userName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupUserAdd($userNameClient, *groupName, *userName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Remove a user from a group.
#
# \param[in]  groupName
# \param[in]  userName  the user to remove from the group
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserRemove(*groupName, *userName, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*status = errorcode(msiSudoGroupMemberRemove(*groupName, *userName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupUserRemove($userNameClient, *groupName, *userName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Promote or demote a group member.
#
# \param[in]  groupName
# \param[in]  userName  the user to promote or demote
# \param[in]  newRole   the new role, either 'manager' or 'user'
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserChangeRole(*groupName, *userName, *newRole, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	uuGroupGetManagers(*groupName, *managers);
	uuListContains(*managers, *userName, *isCurrentlyManager);

	if (*newRole == "manager") {
		if (*isCurrentlyManager) {
			# Nothing to do.
			*status  = 0;
			*message = "";
		} else {
			# Append the user to the managers list.
			*status = errorcode(msiSudoObjMetaAdd(*groupName, "-u", "manager", *userName, "", ""));
			if (*status == 0) {
				*message = "";
			} else {
				uuGroupPolicyCanAddManager($userNameClient, *groupName, *userName, *allowed, *reason);
				if (*allowed == 0) {
					*message = *reason;
				}
			}
		}
	} else if (*newRole == "user") {
		if (*isCurrentlyManager) {
			# Remove the user from the managers list.
			*status = errorcode(msiSudoObjMetaRemove(*groupName, "-u", 0, "manager", *userName, "", ""));
			if (*status == 0) {
				*message = "";
			} else {
				uuGroupPolicyCanRemoveManager($userNameClient, *groupName, *userName, *allowed, *reason);
				if (*allowed == 0) {
					*message = *reason;
				}
			}
		} else {
			# Nothing to do.
			*status  = 0;
			*message = "";
		}
	} else {
		writeLine(
			"serverLog",
			"Invalid group manager call by $userNameClient: User tried to set invalid user role '*newRole'"
		);
	}
}

# }}}
