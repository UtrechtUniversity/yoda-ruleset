# \file
# \brief     Group operation policy checks.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

# \brief ExecCmd policy for group manager commands.
#
# \param[in] cmd
# \param[in] args
# \param[in] addr
# \param[in] hint
#
acPreProcForExecCmd(*cmd, *args, *addr, *hint) {
	ON(*cmd == "group-manager") {
		*allowed = false;

		uuGroupMemberships($userNameClient, *groups)

		# TODO: Parse command strings, call policy checks.
		# TODO: Test these patterns.

		if        (*args like regex "add [^\\\\'\" ]+") {
		} else if (*args like regex "set [^\\\\'\" ]+ [^\\\\'\" ]+ '[^\\\\'\"]+'") {
		} else if (*args like regex "add-user [^\\\\'\" ]+ [^'\\\\'\" ]+") {
		} else if (*args like regex "remove-user [^\\\\'\" ]+ [^'\\\\'\" ]+") {
		}

		if (!*allowed) {
			cut;
			msiOprDisallowed;
			fail;
		}
	}
}

# \brief Check if a user name is valid.
#
# User names must:
#
# - contain zero or one '@' signs, but not at the beginning or the end of the name
# - contain only lowercase letters and hyphens if no '@' sign is present
# - contain only lowercase letters, hyphens, underscores and dots if an '@' sign is present
#   - but: dots may not occur at the beginning or end of the part after the '@'
#
# \param[in] name
#
uuUserNameIsValid(*name)
	= *name like regex ``[a-z-]+|[a-z_.-]+@([a-z_-]+|[a-z_-][a-z_.-]*[a-z_-])``;

# \brief Check if a group name is valid.
#
# Group names must:
#
# - be prefixed with 'grp-'
# - contain only lowercase characters and hyphens
# - not start or end with a hyphen
#
# \param[in] name
#
uuGroupNameIsValid(*name)
	= *name like regex ``grp-([a-z]|[a-z][a-z-]*[a-z])``;

# \brief Check if a (sub)category name is valid.
#
# (sub)Category names must:
#
# - contain only letters, numbers, spaces, hyphens and underscores
# - not start or end in whitespace
# - not contain consecutive whitespace characters
#
# \param[in] name
#
uuGroupCategoryNameIsValid(*name)
	=      *name like regex "[a-zA-Z0-9 _-]+"
	  && !(*name like regex ".*[ ]{2,}.*")
	  &&   *name like regex ".*[^ ]"
	  &&   *name like regex   "[^ ].*";

# \brief Group Policy: Can the user create a new group?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the new group name
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupAdd(*actor, *groupName, *allowed, *reason) {
	*allowed = false;

	uuGroupUserExists("priv-group-add", *actor, *hasPriv);
	if (*hasPriv) {
		if (uuGroupNameIsValid(*groupName)) {
			uuUserNameIsAvailable(*groupName, *nameAvailable, *existingType);
			if (*nameAvailable) {
				*allowed = true;
			} else {
				*reason = "The name '*groupName' is already in use by a *existingType.";
			}
		} else {
			*reason = "Group names must start with 'grp-' and may only contain lowercase letters (a-z) and hyphens (-).";
		}
	} else {
		*reason = "You (*actor) are not a member of the priv-group-add group.";
	}
}

# \brief Group Policy: Can the user create a group with / modify a group to use a certain category?
#
# \param[in]  actor        the user whose privileges are checked
# \param[in]  categoryName the category name
# \param[out] allowed      whether the action is allowed
# \param[out] reason       the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanUseCategory(*actor, *categoryName, *allowed, *reason) {
	*allowed = false;

	uuGroupCategoryExists(*categoryName, *categoryExists);
	if (*categoryExists) {
		*isManagerInCategory = false;

		uuGroupMemberships(*actor, *groupsString);
		foreach (*actorGroup in split(*groupsString, ",")) {
			uuGroupGetCategory(*actorGroup, *agCategory, *agSubcategory);
			if (*agCategory == *categoryName) {
				uuGroupUserIsManager(*actorGroup, *actor, *isManagerInCategory);
				if (*isManagerInCategory) {
					break;
				}
			}
		}
		if (*isManagerInCategory) {
			*allowed = true;
		} else {
			*reason = "You (*actor) are not a group manager in the *categoryName group category.";
		}
	} else {
		uuGroupUserExists("priv-category-add", *actor, *hasPriv);
		if (*hasPriv) {
			if (uuGroupCategoryNameIsValid(*categoryName)) {
				*allowed = true;
			} else {
				*reason = "The new category name is invalid.";
			}
		} else {
			*reason = "You (*actor) are not a member of the priv-category-add group.";
		}
	}
}

# \brief Group Policy: Can the user set a certain group property to a certain value?
#
# Note: The 'administrator' group metadata field is represented in the 'managers'
#       property as a semicolon-separated list of usernames.
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the group name
# \param[in]  property  the group property to set (one of 'category', 'subcategory', 'description', 'managers')
# \param[in]  value     the new value
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupModify(*actor, *groupName, *property, *value, *allowed, *reason) {
	*allowed = false;

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*property == "category") {
			*reason = ""; # The rule engine seems to require us to have our parameters
			              # initialized before passing them to other functions.
			# Defer.
			uuGroupPolicyCanUseCategory(*actor, *value, *allowed, *reason);
		} else if (*property == "subcategory") {
			if (uuGroupCategoryNameIsValid(*value)) {
				*allowed = true;
			} else {
				*reason = "The new subcategory name is invalid.";
			}
		} else if (*property == "managers") {

			*newManagers = split(*value, ";");
			uuListContains(*actor, *newManagers, *hasNotChangedOwnRole);

			if (*hasNotChangedOwnRole) {
				*allowed = true;
			} else {
				*reason = "You cannot demote yourself in group *groupName.";
			}
		} else if (*property == "description") {
			*allowed = true;
		} else {
			*reason = "Invalid group property name.";
		}
	} else {
		*reason = "You (*actor) are not a manager of group *groupName.";
	}
}

# \brief Group Policy: Can the user add a new user to a certain group?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the group name
# \param[in]  newMember the user to add to the group
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupUserAdd(*actor, *groupName, *newMember, *allowed, *reason) {
	*allowed = false;

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (uuUserNameIsValid(*newMember)) {
			*allowed = true;
		} else {
			*reason = "The new member's name is invalid.";
		}
	} else {
		*reason = "You (*actor) are not a manager of group *groupName.";
	}
}

# \brief Group Policy: Can the user remove a user from a certain group?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the group name
# \param[in]  member    the user to remove from the group
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupUserRemove(*actor, *groupName, *member, *allowed, *reason) {
	*allowed = false;

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*member == *actor) {
			*reason = "You cannot remove yourself from group *groupName.";
		} else {
			*allowed = true;
		}
	} else {
		*reason = "You (*actor) are not a manager of group *groupName.";
	}
}
