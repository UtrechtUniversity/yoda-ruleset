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
	ON(*cmd == "group-manager.py") {
		if (
			   *args like regex "add [^\\\\'\" ]+"
			|| *args like regex "set [^\\\\'\" ]+ [^\\\\'\" ]+ '[^\\\\'\"]+'"
			|| *args like regex "add-user [^\\\\'\" ]+ [^'\\\\'\" ]+"
			|| *args like regex "remove-user [^\\\\'\" ]+ [^'\\\\'\" ]+"
		) {
			*allowed = true;
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
# - contain only lowercase characters, numbers and hyphens
# - not start or end with a hyphen
#
# \param[in] name
#
uuGroupNameIsValid(*name)
	= *name like regex ``grp-([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])``;

# \brief Check if a (sub)category name is valid.
#
# Category names must:
#
# - contain only letters, numbers, spaces, commas, periods, underscores and hyphens
#
# \param[in] name
#
uuGroupCategoryNameIsValid(*name)
	= *name like regex ``[a-zA-Z0-9 ,.()_-]+``;

# \brief Group Policy: Can the user create a new group?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the new group name
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupAdd(*actor, *groupName, *allowed, *reason) {
	*allowed = false;
	*reason  = "";

	uuGroupUserExists("priv-group-add", *actor, *hasPriv);
	if (*hasPriv) {
		if (uuGroupNameIsValid(*groupName)) {
			uuUserNameIsAvailable(*groupName, *nameAvailable, *existingType);
			if (*nameAvailable) {
				*allowed = true;
			} else {
				if (*existingType == "rodsuser") {
					*existingType = "user";
				} else if (*existingType == "rodsgroup") {
					*existingType = "group";
				}
				*reason = "The name '*groupName' is already in use by another *existingType.";
			}
		} else {
			*reason = "Group names must start with 'grp-' and may only contain lowercase letters (a-z) and hyphens (-).";
		}
	} else {
		*reason = "You are not a member of the priv-group-add group.";
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
	*reason  = "";

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
			*reason = "You are not a group manager in the *categoryName group category.";
		}
	} else {
		uuGroupUserExists("priv-category-add", *actor, *hasPriv);
		if (*hasPriv) {
			if (uuGroupCategoryNameIsValid(*categoryName)) {
				*allowed = true;
			} else {
				*reason = "(Sub)category names may only contain letters (a-z), numbers, spaces, commas, periods, parentheses, hyphens (-) and underscores (_).";
			}
		} else {
			*reason = "You are not a member of the priv-category-add group.";
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
	*reason  = "";

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
				*reason = "Subcategory names may only contain letters (a-z), numbers, spaces, commas, periods, parentheses, hyphens (-) and underscores (_).";
			}
		} else if (*property == "managers") {
			*newManagers = split(*value, ";");

			uuGroupGetMembers(*groupName, *members);

			*managerListContainsNonMembers = false;
			foreach (*newManager in *newManagers) {
				uuListContains(*newManager, *members, *newManagerIsMember);
				if (!*newManagerIsMember) {
					*managerListContainsNonMembers = true;
					break;
				}
			}
			if (*managerListContainsNonMembers) {
				*reason = "Non-members cannot be made group managers";
			} else {
				uuListContains(*actor, *newManagers, *hasNotChangedOwnRole);

				if (*hasNotChangedOwnRole) {
					*allowed = true;
				} else {
					*reason = "You cannot demote yourself in group *groupName.";
				}
			}
		} else if (*property == "description") {
			*allowed = true;
		} else {
			*reason = "Invalid group property name.";
		}
	} else {
		*reason = "You are not a manager of group *groupName.";
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
	*reason  = "";

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		uuGroupUserExists(*groupName, *newMember, *isAlreadyAMember);
		if (*isAlreadyAMember) {
			*reason = "User '*newMember' is already a member of group '*groupName'.";
		} else {
			if (uuUserNameIsValid(*newMember)) {
				*allowed = true;
			} else {
				*reason = "The new member's name is invalid.";
			}
		}
	} else {
		*reason = "You are not a manager of group *groupName.";
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
	*reason  = "";

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*member == *actor) {
			*reason = "You cannot remove yourself from group *groupName.";
		} else {
			*allowed = true;
		}
	} else {
		*reason = "You are not a manager of group *groupName.";
	}
}
