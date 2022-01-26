# \file      uuGroup.r
# \brief     Functions for group management and group queries.
# \author    Ton Smeele
# \author    Chris Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2021 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

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
		# FIXME: This is not necessarily the local zone.
		#        The local zone could be queried (ZONE_TYPE='local').
		*userZone = $rodsZoneClient;
	}
}

# \brief Retrieve the client zone name.
#
# \param[out] zoneName
#
uuClientZone(*zoneName) {
    *zoneName = $rodsZoneClient;
}

uuClientFullName() = "$userNameClient#$rodsZoneClient";

# \brief Wrapper around uuClientFullName. Enables uuClientFullName to be called
#        from the Python iRODS client
#
# \param[out] fullName
#
uuClientFullNameWrapper(*fullName) {
    *fullName = uuClientFullName();
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
	) {
		if (*row."USER_TYPE" == "rodsuser" || *row."USER_TYPE" == "rodsadmin") {
			*exists = true;
			break;
		}
	}
}

# \brief Check if a user is a member of the given group.
#
# This is now a wrapper for the python function.
#
# \param[in] group        name of the irods group
# \param[in] user         name of the irods user
#                         username can optionally include zone ('user#zone')
#                         default is to use the local zone
# \param[in] includeRo    whether to account for read-only memberships
# \param[out] membership  true if user is a member of this group
#
uuGroupUserExists(*group, *user, *includeRo, *membership) {
        *membership = "";
        rule_group_user_exists(*group, *user, str(*includeRo), *membership);
	if (*membership == "true") {
	        *membership = true;
	} else {
	        *membership = false;
	}
}

# \brief Check if the home collection belonging to a group is empty.
#
# \param[in]  groupName group name (no zone)
# \param[out] empty
#
uuGroupCollIsEmpty(*groupName, *empty) {
	*coll = "/$rodsZoneClient/home/*groupName";
	*empty = true;

	# rods will already be owner of a vault group collection, so no ACLs need
	# to be changed.

	foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = '*coll') {
		*empty = false; break;
	}
	if (*empty) {
		foreach (*row in SELECT COLL_ID WHERE COLL_PARENT_NAME LIKE '*coll') {
			*empty = false; break;
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

	uuGetUserAndZone(*name, *userName, *userZone);

	foreach (
		*row in
		SELECT USER_NAME, USER_ZONE, USER_TYPE
		WHERE  USER_NAME = '*userName'
		  AND  USER_ZONE = '*userZone'
	) {
		*available    = false;
		*existingType = *row."USER_TYPE";
		break;
	}
}

# \brief List all groups the user belongs to.
#
# This result list will include any 'read-*' groups that the user is a member
# of. If this is not desirable, use uuUserGetGroups() instead.
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
		if (*group != *userName) {
			*groups = "*groups:*group";
		}
	}
	*groups = triml(*groups,":");
	*groupList = split(*groups, ":");
}

# \brief Remove an empty vault and any revision collection of a research/intake group that no longer exists.
#
# This will fail if (1) The given vault does not exist,
# or (2) The corresponding research/intake group still exists.
#
# If the vault group is non-empty, it will not be removed, and the rule will succeed.
#
# \param[in] vaultName the group name of the vault to remove
#
uuGroupRemoveOrphanVaultIfEmpty(*vaultName) {
	msiExecCmd("admin-remove-orphan-vault-if-empty.sh",
	           uuClientFullName ++ " " ++ *vaultName,
	           "", "", 0, *out);
	msiGetStdoutInExecCmdOut(*out, *stdout);
	writeString("stdout", "*stdout");
}

# \brief List all groups the user belongs to.
#
# This function has special handling for 'read-*' groups:
#
# If *includeRo is true, any groups that the user is a read-only member of will
# be returned.  E.g. if the user is a member of 'read-test', either
# 'intake-test' or 'research-test' will be returned.
#
# The 'read-...' group names themselves are never included in the result list,
# regardless of the *includeRo parameter.
#
# \param[in]  user      name of the irods user
# \param[in]  includeRo whether to include groups that the user has read-only access to
# \param[out] groups    list of group names
#
uuUserGetGroups(*user, *includeRo, *groups) {

	uuGetUserAndZone(*user, *userName, *userZone);

	*groups     = list();
	*readGroups = list(); # Groups that start with 'read-'.

	foreach (*row in
	         SELECT USER_GROUP_NAME
	         WHERE  USER_NAME = '*userName'
	           AND  USER_ZONE = '*userZone'){

		*groupName = *row.'USER_GROUP_NAME';
		if (*groupName != *userName) {
			if (*groupName like "read-*") {
				# Save 'read-' groups for later processing.
				*readGroups = cons(*groupName, *readGroups);
			} else {
				*groups = cons(*groupName, *groups);
			}
		}
	}

	if (*includeRo) {
		# Map 'read-' groups to their non-read names.
		foreach (*roGroupName in *readGroups) {
			uuGetBaseGroup(*roGroupName, *baseGroup);
			*groups = cons(*baseGroup, *groups);
		}
	}
}

# \brief Map 'read-|vault-' groups to their 'intake-|research-|deposit-' counterparts.
#
# If no base group exists, the input *groupName is returned as *baseGroup.
#
# \param[in]  groupName
# \param[out] baseGroup the base group name
#
uuGetBaseGroup(*groupName, *baseGroup) {

	*baseGroup = "";

	if (*groupName like regex "(read|vault)-.*") {
		uuChop(*groupName, *_, *baseName, "-", true);

		foreach (*row in
				 SELECT USER_GROUP_NAME
				 WHERE  USER_GROUP_NAME LIKE '%-*baseName'){

			*baseLikeGroup = *row.'USER_GROUP_NAME';
			if (*baseLikeGroup like regex "(intake|research|deposit)-*baseName") {
				*baseGroup = *baseLikeGroup;
				break;
			}
		}
	}
	if (*baseGroup == "") {
		# Apparently this group has no counterpart.
		# (or perhaps this isn't a read-|vault- group after all)
		*baseGroup = *groupName;
	}
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

	*subcategories = list();

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
			uuListContains(*subcategories, *subcategoryName, *seen);
			if (!*seen) {
				*subcategories = cons(*subcategoryName, *subcategories);
			}
		}
	}
}

# \brief Get a list of group categories.
#
# \param[out] categories a list of category names
#
uuGroupGetCategories(*categories) {
	*categories = list();
	foreach (
		*category in
		SELECT META_USER_ATTR_VALUE
		WHERE  USER_TYPE           = 'rodsgroup'
		  AND  META_USER_ATTR_NAME = 'category'
	) {
		*categories = cons(*category."META_USER_ATTR_VALUE", *categories);
	}
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
		# Throw away the zone name for backward compat.
		uuChop(*member, *name, *_, "#", true);
		*members = cons(*name, *members);
	}
}

# \brief Get a list of a group's members.
#
# If addTypePrefix is true, usernames will be prefixed with 'r:', 'n:',
# or 'm:', if they are, respectively, a read-only member, normal
# member, or a manager of the given group.
#
# \param[in]  groupName
# \param[in]  includeRo     whether to include members with read-only access
# \param[in]  addTypePrefix whether to prefix user names with the type of member they are (see below)
# \param[out] members       a list of user names, including their zone names
#
uuGroupGetMembers(*groupName, *includeRo, *addTypePrefix, *members) {

	*members = list();

	# Fetch managers.
	uuGroupGetManagers(*groupName, *managers);

	foreach (*manager in *managers) {
		*members = cons(if *addTypePrefix then "m:*manager" else "*manager", *members);
	}

	# Fetch normal members.
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

	# Fetch read-only members.
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
		WHERE  USER_GROUP_NAME     = '*groupName'
		  AND  META_USER_ATTR_NAME = 'manager'
	) {
		# For backward compatibility, let zone be $rodsZoneClient if
		# it's not present in metadata.
		uuGetUserAndZone(*manager."META_USER_ATTR_VALUE", *name, *zone);

		# Verify that this manager is actually a member of the group.
		# (this is necessary for a.o. the groupUserAdd policy to work correctly
		# when creating a new group)
		uuGroupUserExists(*groupName, "*name#*zone", false, *isMember);

		if (*isMember) {
			*managers = cons("*name#*zone", *managers);
		}
	}
}

# \brief Find users matching a pattern.
#
# \param[in]  query
# \param[out] users a list of user names
#
uuFindUsers(*query, *users) {
	*userList = list();

	*queryUser = *query;
	*queryZone = "";

	if (*query like "*#*") {
		# Use the user and zone part as separate wildcard-surrounded query
		# parts.
		uuChop(*query, *queryUser, *queryZone, "#", true);
	}

	foreach (
		*user in
		SELECT USER_NAME, USER_ZONE
		WHERE  USER_TYPE = 'rodsuser'
		  AND  USER_NAME LIKE '%*queryUser%'
		  AND  USER_ZONE LIKE '%*queryZone%'
	) {
		*userList = cons(*user."USER_NAME" ++ "#" ++ *user."USER_ZONE", *userList);
	}
	foreach (
		*user in
		SELECT USER_NAME, USER_ZONE
		WHERE  USER_TYPE = 'rodsadmin'
		  AND  USER_NAME LIKE '%*queryUser%'
		  AND  USER_ZONE LIKE '%*queryZone%'
	) {
		*userList = cons(*user."USER_NAME" ++ "#" ++ *user."USER_ZONE", *userList);
	}

	uuJoin(',', *userList, *users)
}

# \brief Check if a user is a manager in the given group.
#
# \param[in]  groupName
# \param[in]  user
# \param[out] isManager
#
uuGroupUserIsManager(*groupName, *user, *isManager) {
	*isManager = false;

	uuGetUserAndZone(*user, *name, *zone);
	*fullName = "*name#*zone";

	if (*groupName like "read-*") {
		uuGetBaseGroup(*groupName, *baseGroup);
		if (*baseGroup != *groupName) {
			# Check manager status on the base group instead.
			uuGroupUserIsManager(*baseGroup, *fullName, *isManager);
		}

	} else {
		uuGroupUserExists(*groupName, *fullName, false, *isMember);
		if (*isMember) {
			foreach (
				*manager in
				SELECT META_USER_ATTR_VALUE
				WHERE  USER_GROUP_NAME      = '*groupName'
				  AND  META_USER_ATTR_NAME  = 'manager'
				  AND  META_USER_ATTR_VALUE = '*fullName'
			) {
				*isManager = true;
			}
		}
	}
}

# \brief Get a user's member role type.
#
# \param[in]  groupName the group name
# \param[in]  user      the member name, optionally including their zone name
# \param[out] type      the type of member, one of 'none', 'reader', 'normal' or 'manager'
#
uuGroupGetMemberType(*groupName, *user, *type) {

	# {{{

	# For some great inexplicable reason, the following is completely broken:

	# {
	#uuGetUserAndZone(*user, *userName, *userZone);
	#writeLine("serverLog", "*user -> *userName # *userZone");

	#uuGroupGetMembers(*groupName, true, true, *members);
	#writeLine("serverLog", "*user -> *userName # *userZone");
	# }

	# The above call to uuGroupGetMembers OVERWRITES *userName with a different
	# one, even though *userName is not even a parameter to that function.
	# This has happened consistently when this rule is called as part of
	# demoting a user (normal -> reader) from the group management portal.
	# Unfortunately, I can't reproduce it via irule when calling this rule
	# directly.

	# As a workaround..... use a different variable name for userName and userZone.
	# Yes. That fixes it. Don't ask me why.

	# {
	uuGetUserAndZone(*user, *userName1, *userZone1);

	uuGroupGetMembers(*groupName, true, true, *members);

	*userName = *userName1;
	*userZone = *userZone1;
	# }

	# }}}

	*type = "none";

	foreach (*member in *members) {
		uuChop(*member, *typeLetter, *member, ":", true);
		if (*member == "*userName#*userZone") {
			     if (*typeLetter == "r") { *type = "reader";  }
			else if (*typeLetter == "m") { *type = "manager"; }
			else                         { *type = "normal";  }
			break;
		}
	}
}

# Privileged group management functions {{{

# \brief Create a group.
#
# \param[in]  groupName
# \param[out] status  '0' on success, non-zero on failure - as string value!
# \param[out] message a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupAdd(*groupName, *category, *subcategory, *description, *dataClassification, *status, *message) {
	*status  = '0';
	*message = "An internal error occurred";

        # Safeguard the maximum length of a group
        *nameLength = strlen(*groupName);
        if (*nameLength > 63) {
            *status = '999';
            *message = "The groupname '*groupName' is too long (" ++ str(*nameLength) ++ "). The maximum allowed number of characters is 63";
            succeed;
        }

	if (*description == "") {
		# XXX This exact workaround exists in the `uuGroupModify` rule as well.
		#     If you change this block, change it there too.

		# Work around an iRODS bug that causes errors when changing metadata
		# values to an empty string in specific situations.
		# 'description' is currently the only property that can be set to empty
		# by the user, and we handle that case here.
		*description = ".";
		# This dot must be treated specially (as an empty string) in query
		# functions.
	}

	*kv."category"            = *category;
	*kv."subcategory"         = *subcategory;
	*kv."description"         = *description;
	*kv."data_classification" = *dataClassification;

	# Shoot first, ask questions later.
        *status = str(errorcode(msiSudoGroupAdd(*groupName, "manager", uuClientFullName, "", *kv)));

	if (*status == '0') {
		*message = "";
	} else {
		# Why didn't you allow me to do that?
		uuGroupPolicyCanGroupAdd(
			uuClientFullName,
			*groupName,
			*category,
			*subcategory,
			*description,
			*dataClassification,
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
# This is mostly a shortcut for setting single-value attributes on a group
# object. Allowed properties are: 'category', 'subcategory', 'description', and
# 'data_classification'.
#
# \param[in]  groupName
# \param[in]  property  the property to change
# \param[in]  value     the new property value
# \param[out] status    '0' on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupModify(*groupName, *property, *value, *status, *message) {
	*status  = '1';
	*message = "An internal error occurred.";

	*kv.'.' = ".";

	if (*value == "") {
		# XXX This exact workaround exists in the `uuGroupAdd` rule as well.
		#     If you change this block, change it there too.

		# Work around an iRODS bug that causes errors when changing metadata
		# values to an empty string in specific situations.
		# 'description' is currently the only property that can be set to empty
		# by the user, and we handle that case here.
		*value = ".";
		# This dot must be treated specially (as an empty string) in query
		# functions.
	}

	if (*property == "category") {
		# We must pass the current category name such that the postproc rule
		# for metaset can revoke read access from the current datamanager group
		# in our category if it exists.

		uuGroupGetCategory(*groupName, *category, *_);
		*kv.'oldCategory' = *category;
	}

	*status = str(errorcode(msiSudoObjMetaSet(*groupName, "-u", *property, *value, "", *kv)));
	if (*status == '0') {
		*message = "";
	} else {
		uuGroupPolicyCanGroupModify(uuClientFullName, *groupName, *property, *value, *allowed, *reason);
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
	*message = "An internal error occurred.";

	*status = errorcode(msiSudoGroupRemove(*groupName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupRemove(uuClientFullName, *groupName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Modify a user.
#
# This is mostly a shortcut for setting single-value attributes on a user
# object.
#
# \param[in]  userName
# \param[in]  property  the property to change
# \param[in]  value     the new property value
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuUserModify(*userName, *property, *value, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

	*kv.'.' = ".";

	if (*value == "") {
		# XXX This exact workaround exists in the `uuGroupAdd` rule as well.
		#     If you change this block, change it there too.

		# Work around an iRODS bug that causes errors when changing metadata
		# values to an empty string in specific situations.
		# 'description' is currently the only property that can be set to empty
		# by the user, and we handle that case here.
		*value = ".";
		# This dot must be treated specially (as an empty string) in query
		# functions.
	}

	*status = errorcode(msiSudoObjMetaSet(*userName, "-u", *property, *value, "", *kv));
	if (*status == 0) {
		*message = "";
	} else {
		uuUserPolicyCanUserModify(uuClientFullName, *userName, *property, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Remove user metadata.
#
# \param[in]  userName
# \param[in]  property  the property to remove
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuUserMetaRemove(*userName, *property, *status, *message) {
	*status  = 1;
	*message = "An internal error occured.";

    *status = errorcode(msiSudoObjMetaRemove(*userName, "-u", "wildcards", *property, "", "", ""));
    if (*status == 0) {
		*message = "";
	} else {
		uuUserPolicyCanUserModify(uuClientFullName, *userName, *property, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Check that a user is external.
#
# \param[in] userName   the user to check
#
uuExternalUser(*userName) {
	*nameAndDomain = split(*userName, "@");
	if (size(*nameAndDomain) == 2) {
		*domain = elem(*nameAndDomain, 1);
		if (*domain != "uu.nl" && *domain not like "*.uu.nl") {
			# is external
			true;
		} else {
			false;
		}
	} else {
		false;
	}
}

# \brief Add a user to a group.
#
# \param[in]  groupName
# \param[in]  user      the user to add to the group
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserAdd(*groupName, *user, *status, *message) {
	*status  = 1;
	*message = "An internal error occurred.";

	uuGetUserAndZone(*user, *userName, *userZone);
	*fullName = "*userName#*userZone";

	uuUserExists(*fullName, *exists);

	# User does not exist, add user to iRODS first.
	if (!*exists) {
		*kv."forGroup" = *groupName;
		*status = errorcode(msiSudoUserAdd(*fullName, "", "", "", *kv));
		if (*status != 0) {
			uuGroupPolicyCanGroupUserAdd(uuClientFullName, *groupName, *fullName, *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed; # Return here (fail would ruin the status and error message).
		}

                # Provision external user.
                if (uuExternalUser(*userName)) {
                        *http_code = ""
                        *message = ""
                        rule_group_provision_external_user(*userName, $userNameClient, $rodsZoneClient, *http_code, *message);
                        if (*message != "") {
                                writeLine("serverLog", "[EXTERNAL USER] *message");
                                *status = int(*http_code)
                                succeed; # Return here (fail would ruin the status and error message).
                        }
                        writeLine("serverLog", "[EXTERNAL USER] User *userName added by $userNameClient on $rodsZoneClient.");
                }
	}

	# User exists, now add them to the group.
	*status = errorcode(msiSudoGroupMemberAdd(*groupName, *fullName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupUserAdd(uuClientFullName, *groupName, *fullName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Remove a user from a group.
#
# \param[in]  groupName
# \param[in]  user      the user to remove from the group
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserRemove(*groupName, *user, *status, *message) {
	*status  = 1;
	*message = "An internal error occurred.";

	uuGetUserAndZone(*user, *userName, *userZone);
	*fullName = "*userName#*userZone";

	uuGroupGetMemberType(*groupName, *fullName, *role);
	*actualGroupToRemoveUserFrom = *groupName;

	if (*role == "reader") {
		uuChop(*groupName, *_, *baseName, "-", true);
		*actualGroupToRemoveUserFrom = "read-*baseName";
	}

	*status = errorcode(msiSudoGroupMemberRemove(*actualGroupToRemoveUserFrom, *fullName, ""));
	if (*status == 0) {
		*message = "";
	} else {
		uuGroupPolicyCanGroupUserRemove(uuClientFullName, *groupName, *fullName, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		}
	}
}

# \brief Promote or demote a group member.
#
# \param[in]  groupName
# \param[in]  user      the user to promote or demote
# \param[in]  newRole   the new role, one of 'reader', 'normal', or 'manager'
# \param[out] status    zero on success, non-zero on failure
# \param[out] message   a user friendly error message, may contain the reason why an action was disallowed
#
uuGroupUserChangeRole(*groupName, *user, *newRole, *status, *message) {
	*status  = 1;
	*message = "An internal error occurred.";

	uuGetUserAndZone(*user, *userName, *userZone);
	*fullName = "*userName#*userZone";

	uuGroupGetMemberType(*groupName, *fullName, *oldRole);

	if (*newRole == *oldRole) {
		# Nothing to do.
		*status  = 0;
		*message = "";

		succeed;
	}

	# Since changing a user's role within a group can be a multi-step process,
	# we need to check for permission before we try to change things.
	# For example: When changing a role from 'normal' to 'reader', the client may be
	# allowed to remove the user from the base group, but there might not be a
	# read group defined for the base group at all.
	uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);
	if (*allowed == 0) {
		*message = *reason;
		succeed;
	}

	# Readers can only be promoted, managers can only be demoted.
	# The first step if the user is of either type is to promote / demote them
	# one step to the "normal" member role.
	if (*oldRole == "reader") {
		uuChop(*groupName, *_, *baseName, "-", true);
		*roGroup = "read-*baseName";
		*status = errorcode(msiSudoGroupMemberRemove(*roGroup, *fullName, ""));

		if (*status != 0) {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, "normal", *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}

		# Add the user to the group to make them a normal member.

		*status = errorcode(msiSudoGroupMemberAdd(*groupName, *fullName, ""));
		if (*status == 0) {
			*message = "";
		} else {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, "normal", *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}

	} else if (*oldRole == "manager") {
		*status = errorcode(msiSudoObjMetaRemove(*groupName, "-u", "", "manager", *fullName, "", ""));
		if (*status != 0) {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, "normal", *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}

	} else if (*oldRole == "none") {
		# For the sake of clear error reporting, we must detect the situation
		# in which the user is not a member of the group at all.

		# We delegate the generation of the appropriate error message to the
		# policy check function.

		uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);

		if (*allowed == 0) {
			*message = *reason;
		} else {
			*status = 1; # This shouldn't be allowed, abort abort!
		}
		succeed;
	}

	# The user is now a normal member.

	if (*newRole == "normal") {

		# Nothing to do :)
		*message = "";

	} else if (*newRole == "reader") {

		# Remove the user from the normal group.

		*status = errorcode(msiSudoGroupMemberRemove(*groupName, *fullName, ""));

		if (*status != 0) {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}

		# Add the user to the read group.

		uuChop(*groupName, *_, *baseName, "-", true);
		*roGroup = "read-*baseName";

		*status = errorcode(msiSudoGroupMemberAdd(*roGroup, *fullName, ""));
		if (*status == 0) {
			*message = "";
		} else {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}
	} else if (*newRole == "manager") {

		# Add manager metadata.

		*status = errorcode(msiSudoObjMetaAdd(*groupName, "-u", *newRole, *fullName, "", ""));
		if (*status == 0) {
			*message = "";
		} else {
			uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);
			if (*allowed == 0) {
				*message = *reason;
			}
			succeed;
		}
	} else {

		# We do not recognize this role - let the policy check function figure it out.
		uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *groupName, *fullName, *newRole, *allowed, *reason);
		if (*allowed == 0) {
			*message = *reason;
		} else {
			# An unimplemented but allowed role, this should not happen.
			*status = 1;
		}
		succeed;
	}
}
