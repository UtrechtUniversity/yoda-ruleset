# \file
# \brief     Group operation policy check rules.
# \author    Chris Smeele
# \author    Ton Smeele
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015 - 2021, Utrecht University. All rights reserved
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

# \brief Check if a group name is valid for creation by a priv-group-add member.
#
# Group names must:
#
# - be prefixed with 'intake-' or 'research-' or 'deposit-'
# - contain only lowercase characters, numbers and hyphens
# - not start or end with a hyphen
#
# NB: Update the category name check below if you change the second half of this pattern.
#
# NB: Datamanager is missing in this list. It can only be created by rodsadmin,
#     and rodsadmin currently bypasses all checks anyway.
#     This check is applicable only to rodsusers with priv-group-add.
#
# \param[in] name
#
uuGroupNameIsValid(*name)
	= *name like regex ``(intake|research|deposit)-([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])``;

# \brief Check if a category name is valid.
#
# This must be exactly the same as the part of the group name check after the group prefix.
#
# \param[in] name
#
uuGroupCategoryNameIsValid(*name)
	= *name like regex ``([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])``;

# \brief Check if a subcategory name is valid.
#
# Subcategory names must:
#
# - contain only letters, numbers, spaces, commas, periods, underscores and hyphens
#
# \param[in] name
#
uuGroupSubcategoryNameIsValid(*name)
	= *name like regex ``[a-zA-Z0-9 ,.()_-]+``;

# \brief Check if a data classification is valid in combination with a group name.
#
# The valid set of classifications depends on the group prefix.
#
# \param[in]  groupName
# \param[in]  dataClassification
# \param[out] valid
#
uuGroupDataClassificationIsValid(*groupName, *dataClassification, *valid) {
	uuChop(*groupName, *prefix, *base, "-", true);
	if (*prefix == "research" || *prefix == "intake") {
		uuListContains(list("critical", "sensitive", "basic", "public", "unspecified"), *dataClassification, *valid);
	} else {
		*valid = (*dataClassification == "");
	}
}

# \brief Check if a schema-id is valid.
#
# \param[in]  schema_id
# \param[out] valid
#
uuGroupSchemaIdIsValid(*schema_id, *valid) {
    # Check validity of schema_id
    *schema_coll = "/$rodsZoneClient/yoda/schemas/" ++ *schema_id;
    *coll = "";
    foreach(*row in SELECT COLL_NAME WHERE COLL_NAME = *schema_coll) {
        *coll = *row.COLL_NAME;
        succeed;
    }

    if (*coll != "") {
        *valid = true;
    } else {
        *valid = false;
    }
}

# \brief Check if indicated retention period is valid
#
# \param[in]  retention_period
# \param[out] valid
#
uuGroupRetentionPeriodIsValid(*retention_period, *valid) {
    *result = "";
    writeLine("serverLog","IN uuGroupRetentionPeriodIsValid::::: retent_period:  *retention_period ");
    rule_group_retention_period_validate(*retention_period, *result);
    writeLine("serverLog","IN uuGroupRetentionPeriodIsValid::::: result: *result ");
    *valid = bool(*result);
}

# }}}

# \brief Group Policy: Can the user create a new group?
#
# \param[in]  actor       the user whose privileges are checked
# \param[in]  groupName   the new group name
# \param[in]  category
# \param[in]  subcategory
# \param[in]  schema_id
# \param[in]  retention_period
# \param[in]  description
# \param[in]  dataClassification
# \param[out] allowed     whether the action is allowed
# \param[out] reason      the reason why the action was disallowed, set if allowed is false
#
uuGroupPolicyCanGroupAdd(*actor, *groupName, *category, *subcategory, *schema_id, *retention_period, *description, *dataClassification, *allowed, *reason) {
    # Rodsadmin exception.
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; writeLine("serverLog","In CanGroupAdd RODSADMIN");}

	*allowed = 0;
	*reason  = "";

	uuGroupUserExists("priv-group-add", *actor, false, *hasPriv);
	if (*hasPriv) {
		if (uuGroupNameIsValid(*groupName)) {
			uuUserNameIsAvailable(*groupName, *nameAvailable, *existingType);
			if (*nameAvailable) {

				uuGroupDataClassificationIsValid(*groupName, *dataClassification, *dataclasValid);

				if (*dataclasValid) {

					uuChop(*groupName, *prefix, *base, "-", true);

					# For research and intake groups: Make sure their ro and
					# vault groups do not exist yet.
					*roName = "read-*base";
					uuGroupExists(*roName, *roExists);

					*vaultName = "vault-*base";
					uuGroupExists(*vaultName, *vaultExists);
					# Extra check for situations that a vault path is already present
					uuGroupVaultPathExists(*vaultName, *vaultPathExists);

					if (*roExists || *vaultExists || *vaultPathExists) {
						*reason = "This group name is not available.";
					} else {
						uuGroupSchemaIdIsValid(*schema_id, *schemaIdValid);
						if (*schemaIdValid) {
                                                    # Check retention period
                                                    uuGroupRetentionPeriodIsValid(*retention_period, *retentionPeriodValid);
                                                    if (*retentionPeriodValid) {
							# Last check.
							uuGroupPolicyCanUseCategory(*actor, *category, *allowed, *reason);
                                                    } else {
                                                        *reason = "Invalid retention period when adding group: '*retention_period'";
                                                    }
						} else {
							# schema not valid -> report error
							*reason = "Invalid schema-id used when adding group: '*schema_id'";
						}
					}
				} else {
					*reason = "The chosen data classification is invalid for this type of group.";
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
			*reason = "Group names must start with one of 'intake-' or 'research-' or 'deposit-' and may only contain lowercase letters (a-z) and hyphens (-).";
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
		uuGroupUserExists("priv-category-add", *actor, false, *hasPriv);
		if (*hasPriv) {
			if (uuGroupCategoryNameIsValid(*categoryName)) {
				*allowed = 1;
			} else {
				*reason = "Category names may only contain lowercase letters (a-z), numbers, and hyphens (-), and may not start or end with a hyphen.";
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
# \param[in]  attribute the group attribute to set (one of 'category', 'subcategory', 'description', 'data_classification', 'schema_id', 'retention_period')
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
			if (*groupName like "datamanager-*" && *groupName != "datamanager-*value") {
				*reason = "The category of a datamanager group cannot be changed.";
			} else {
				uuGroupPolicyCanUseCategory(*actor, *value, *allowed, *reason);
			}

		} else if (*attribute == "subcategory") {
			if (uuGroupSubcategoryNameIsValid(*value)) {
				*allowed = 1;
			} else {
				*reason = "Subcategory names may only contain letters (a-z), numbers, spaces, commas, periods, parentheses, hyphens (-) and underscores (_).";
			}
		} else if (*attribute == "description") {
			*allowed = 1;
		} else if (*attribute == "data_classification") {
			uuGroupDataClassificationIsValid(*groupName, *value, *dataClassValid);
			if (*dataClassValid) {
				*allowed = 1;
			} else {
				*reason = "The chosen data classification is invalid for this type of group.";
			}
		} else if (*attribute == "schema_id") {
			uuGroupSchemaIdIsValid(*value, *schemaIdValid);
			if (*schemaIdValid) {
				*allowed = 1;
			} else {
				*reason = "The chosen schema id is invalid for this group.";
			}

                } else if (*attribute == "retention_period") {
                        uuGroupRetentionPeriodIsValid(*value, *retentionPeriodValid);
                        if (*retentionPeriodValid) {
                                *allowed = 1;
                        } else {
                                *reason = "The indicated retention period is invalid";
                        }

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
		#                           v  These groups are user-removable  v
		if (*groupName like regex "(grp|intake|research|deposit|vault)-.*") {
			# NB: Only rodsadmin can remove datamanager groups.
			#     Even datamanager group managers cannot remove their own group.
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

	uuGroupGetMemberCount(*groupName, *members);

	if (int(*members) == 0 && *newMember == *actor) {
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
			uuGroupUserExists(*groupName, *newMember, false, *isAlreadyAMember);
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
			|| (*newRole == "reader" && *groupName like regex "(intake|research|deposit)-.*")) {

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

# \brief User Policy: Can the user set a certain user attribute to a certain value?
#
# \param[in]  actor     the user whose privileges are checked
# \param[in]  userName  the user name
# \param[in]  attribute the user attribute to set
# \param[out] allowed   whether the action is allowed
# \param[out] reason    the reason why the action was disallowed, set if allowed is false
#
uuUserPolicyCanUserModify(*actor, *userName, *attribute, *allowed, *reason) {
	uuGetUserType(*actor, *actorUserType);
	if (*actorUserType == "rodsadmin") { *allowed = 1; *reason = ""; succeed; }

	*allowed = 0;
	*reason  = "";

    # User setting: mail notifications
    if (*attribute == "org_settings_mail_notifications") {
        if (*actor == *userName) {
            *allowed = 1;
        } else {
            *reason = "Cannot modify settings of other user.";
        }
    # User notifications
    } else if (trimr(*attribute, "_") == "org_notification") {
        *allowed = 1;
	} else {
		*reason = "Invalid user attribute name.";
	}
}
