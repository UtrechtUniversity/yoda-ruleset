# \file
# \brief     Group operation policy check rules.
# \author    Chris Smeele
# \author    Ton Smeele
# \copyright Copyright (c) 2015 - 2017, Utrecht University. All rights reserved
# \license   GPLv3, see LICENSE

# For every Group Management action (GroupAdd, GroupUserChangeRole, etc.) there
# is a corresponding function in this file that will tell you if someone (the
# *actor) is allowed to perform that action with the supplied parameters.
#
# The result is returned in the output parameters *allowed and *reason. For
# calling rules to be able to receive these output parameters, it is imperative
# that the rules in this file DO NOT FAIL.
#
# Context: The rules in this file are called by:
# - Group Manager implementations of Sudo policies (see uuGroupPolicies.r)
# - Group Manager actions, to figure out the reason for denying a Sudo action.

# Utility functions {{{

# \brief Check if a user name is valid.
#
# User names must:
#
# - contain zero or one '@' signs, but not at the beginning or the end of the name
# - contain only lowercase letters and dots if no '@' sign is present
# - contain only lowercase letters, numbers, hyphens, underscores and dots if an '@' sign is present
# - may contain a zone name after a '#' sign
#
# \param[in] name
#
uuUserNameIsValid(*name)
	= *name like regex ``([a-z.]+|[a-z0-9_.-]+@[a-z0-9_.-]+)(#[a-zA-Z0-9_-]+)?``;

# \brief Check if a group name is valid.
#
# Group names must:
#
# - be prefixed with 'intake-' or 'research-'
# - contain only lowercase characters, numbers and hyphens
# - not start or end with a hyphen
#
# \param[in] name
#
uuGroupNameIsValid(*name)
	= *name like regex ``(intake|research)-([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])``;

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

# }}}

# \brief Group Policy: Can the user create a new group?
#
# \param[in]  actor       the user whose privileges are checked
# \param[in]  groupName   the new group name
# \param[in]  category
# \param[in]  subcategory
# \param[in]  description
# \param[out] allowed     whether the action is allowed
# \param[out] reason      the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupAdd(*actor, *groupName, *category, *subcategory, *description, *allowed, *reason) {
    # Rodsadmin exception.
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupUserExists("priv-group-add", *actor, *hasPriv);
	if (*hasPriv) {
		if (uuGroupNameIsValid(*groupName)) {
			uuUserNameIsAvailable(*groupName, *nameAvailable, *existingType);
			if (*nameAvailable) {

				uuChop(*groupName, *_, *base, "-", true);
				*roName = "read-*base";
				uuGroupExists(*roName, *roExists);

				if (*roExists) {
					*reason = "This group name is not available.";
				} else {
					# Last check.
					uuGroupPolicyCanUseCategory(*actor, *category, *allowed, *reason);
				}

			} else {
				if (*existingType == "rodsuser") {
					*existingType = "user";
				} else if (*existingType == "rodsgroup") {
					*existingType = "group";
				}
				*reason = "The name '*groupName' is already in use by another *existingType.";
			}
		} else {
			*reason = "Group names must start with one of 'intake-', 'research-', or 'datamanagers-' and may only contain lowercase letters (a-z) and hyphens (-).";
		}
	} else {
		*reason = "You cannot create groups because you are not a member of the priv-group-add group.";
	}
}

# \brief Group Policy: Can the user create a group with / modify a group to use a certain category?
#
# This is a utility function for other check functions, there is no
# corresponding group action for this rule.
#
# \param[in]  actor        the user whose privileges are checked
# \param[in]  categoryName the category name
# \param[out] allowed      whether the action is allowed
# \param[out] reason       the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanUseCategory(*actor, *categoryName, *allowed, *reason) {
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupCategoryExists(*categoryName, *categoryExists);
	if (*categoryExists) {
		*isManagerInCategory = false;

		uuUserGetGroups(*actor, false, *groups);

		foreach (*actorGroup in *groups) {
			uuGroupGetCategory(*actorGroup, *agCategory, *agSubcategory);
			if (*agCategory == *categoryName) {
				uuGroupUserIsManager(*actorGroup, *actor, *isManagerInCategory);
				if (*isManagerInCategory) {
					break;
				}
			}
		}
		if (*isManagerInCategory) {
			*allowed = 1;
		} else {
			*reason = "You cannot use this group category because you are not a group manager in the *categoryName category.";
		}
	} else {
		uuGroupUserExists("priv-category-add", *actor, *hasPriv);
		if (*hasPriv) {
			if (uuGroupCategoryNameIsValid(*categoryName)) {
				*allowed = 1;
			} else {
				*reason = "(Sub)category names may only contain letters (a-z), numbers, spaces, commas, periods, parentheses, hyphens (-) and underscores (_).";
			}
		} else {
			*reason = "You cannot use this group category because you are not a member of the priv-category-add group.";
		}
	}
}

# \brief Group Policy: Can the user set a certain group attribute to a certain value?
#
# Available attributes are: category, subcategory and description.
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the group name
# \param[in]  attribute the group attribute to set (one of 'category', 'subcategory', 'description')
# \param[in]  value     the new value
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#

uuGroupPolicyCanGroupModify(*actor, *groupName, *attribute, *value, *allowed, *reason) {
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*attribute == "category") {
			*reason = ""; # The rule engine seems to require us to have our parameters
			              # initialized before passing them to other functions.

			uuGroupPolicyCanUseCategory(*actor, *value, *allowed, *reason);

		} else if (*attribute == "subcategory") {
			if (uuGroupCategoryNameIsValid(*value)) {
				*allowed = 1;
			} else {
				*reason = "Subcategory names may only contain letters (a-z), numbers, spaces, commas, periods, parentheses, hyphens (-) and underscores (_).";
			}
		} else if (*attribute == "description") {
			*allowed = 1;
		} else {
			*reason = "Invalid group attribute name.";
		}
	} else {
		*reason = "You are not a manager of group *groupName.";
	}
}

# \brief Group Policy: Can the user remove a group?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName the group name
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupRemove(*actor, *groupName, *allowed, *reason) {
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*groupName like regex "(grp|intake|research|vault)-.*") {
			*homeCollection = "/$rodsZoneClient/home/*groupName";
			*homeCollectionIsEmpty = true;

			foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = '*homeCollection') {
				*homeCollectionIsEmpty = false; break;
			}
			foreach (*row in SELECT COLL_ID WHERE COLL_PARENT_NAME LIKE '*homeCollection') {
				*homeCollectionIsEmpty = false; break;
			}

			if (*homeCollectionIsEmpty) {
				*allowed = 1;
			} else {
				*reason = "The group's directory is not empty. Please remove all of its files and subdirectories before removing this group.";
			}
		} else {
			*reason = "'*groupName' is not a regular group. You can only remove groups that have one of the following prefixes: grp, intake, research, vault.";
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
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupGetMembers(*groupName, true, false, *members);

	if (size(*members) == 0 && *newMember == *actor) {
		# Special case for empty groups.
		# This is run if a group has just been created. We then allow
		# the group creator (already set in the 'manager' field by the
		# postproc of GroupAdd) to add himself to the group.
		*isCreator = false;
		foreach (
			*manager in
			SELECT META_USER_ATTR_VALUE
			WHERE  USER_GROUP_NAME      = '*groupName'
			  AND  META_USER_ATTR_NAME  = 'manager'
			  AND  META_USER_ATTR_VALUE = '*newMember'
		) {
			*isCreator = true;
		}
		if (*isCreator) {
			*allowed = 1;
		} else {
			*reason = "You are not a manager of group '*groupName'.";
		}
	} else {
		uuGroupUserIsManager(*groupName, *actor, *isManager);
		if (*isManager) {
			uuGroupUserExists(*groupName, *newMember, *isAlreadyAMember);
			if (*isAlreadyAMember) {
				*reason = "User '*newMember' is already a member of group '*groupName'.";
			} else {
				if (uuUserNameIsValid(*newMember)) {
					*allowed = 1;
				} else {
					*reason = "The new member's name is invalid.";
				}
			}
		} else {
			*reason = "You are not a manager of group *groupName.";
		}
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
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

	uuGroupUserIsManager(*groupName, *actor, *isManager);
	if (*isManager) {
		if (*member == *actor) {
			# This also ensures that groups always have at least one manager.
			*reason = "You cannot remove yourself from group *groupName.";
		} else {
			*allowed = 1;
		}
	} else {
		*reason = "You are not a manager of group *groupName.";
	}
}

# \brief Group Policy: Can the user change a group member's role?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  groupName
# \param[in]  member    the target group member
# \param[in]  newRole   the member's new role
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupUserChangeRole(*actor, *groupName, *member, *newRole, *allowed, *reason) {
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason = "";

	uuGroupUserExists(*groupName, *member, true, *exists);

	if (*exists) {
		if (   (*newRole == "normal" || *newRole == "manager")
			|| (*newRole == "reader" && *groupName like regex "(intake|research)-.*")) {

			uuGroupUserIsManager(*groupName, *actor, *isManager);
			if (*isManager) {
				if (*member == *actor) {
					*reason = "You cannot change your own role in group *groupName.";
				} else {
					*allowed = 1;
				}
			} else {
				*reason = "You are not a manager of group *groupName.";
			}
		} else {
			*reason = "'*newRole' is not a valid member role for group *groupName.";
		}
	} else {
		*reason = "'*member' is not a member of group *groupName.";
	}
}
