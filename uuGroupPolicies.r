# \file      uuGroupPolicies.r
# \brief     Sudo microservices policy implementations for group manager.
# \author    Chris Smeele
# \copyright Copyright (c) 2016-2018, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# This file contains Group Manager implementations of pre- and postproc rules
# for Sudo actions.
#
# See the uuSudoPolicies.r file for other (non-GM) implementations of pre- and
# postproc rules for the sudo microservices.
#
# Only "low level" checks are implemented in these rules. When a sudo action
# can be translated to a Group Manager action*, a corresponding "high level"
# check is called in uuGroupPolicyChecks.r.
#
# * There is a mapping from Group Manager actions (e.g. GroupUserRemove) to one
#   or more Sudo actions (GroupMemberRemove). In some cases this mapping is
#   1:1, while for others (notably ChangeRole), it's complicated.
#
# Additionally, certain features which are not directly exposed in Group
# Manager actions, such as the existence of 'read-*' groups, are handled in
# these rules.

# Preprocessing rules. {{{

uuGroupPreSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) {

	if (*initialAttr != "") { fail; }

	# If the actor can add the user to a group, allow them to create the user.
	uuGroupPolicyCanGroupUserAdd(
		uuClientFullName,
		*policyKv."forGroup",
		*userName,
		*allowed, *reason
	);
	if (*allowed == 1) {
		succeed;
	}

	fail;
}

uuGroupPreSudoUserRemove(*userName, *policyKv) {

	# Do not allow user deletion.

	fail;
}

uuGroupPreSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {

	if (*groupName like regex "(read|vault)-.*") {

		# This type of group is automatically created from a postproc policy.

		uuGetBaseGroup(*groupName, *baseName);
		if (*baseName == *groupName) {
			# Do not allow creating a standalone "read-" or "vault-" group.
			# There must always be a corresponding "intake-" or "research-" group.
			fail;
		}

		uuGroupUserIsManager(*baseName, uuClientFullName, *isManagerInBaseGroup);
		if (!*isManagerInBaseGroup) {
			# Only allow creation of a read or vault group if the creator is a
			# manager in the base group. (research or intake).
			fail;
		}

		succeed;

	} else {

		# This type of group is manually created.

		if (*initialAttr == "manager" || *initialValue == uuClientFullName) {
			# Normal groups must have an initial manager attribute.

			# Now check the higher level policy.
			uuGroupPolicyCanGroupAdd(
				uuClientFullName,
				*groupName,
				*policyKv."category",
				*policyKv."subcategory",
				*policyKv."description",
				*policyKv."data_classification",
				*allowed, *reason
			);
			if (*allowed == 1) {
				succeed;
			}
		}
	}

	fail;
}

uuGroupPreSudoGroupRemove(*groupName, *policyKv) {

	if (*groupName like "read-*") {
		uuGetBaseGroup(*groupName, *baseGroup);
		if (*baseGroup == *groupName) {
			# If there's no base group [anymore], anyone can delete the read
			# group.
			# This is less than desirable, but there is currently no way to
			# know if the actor was a manager of the base group, since the base
			# group no longer exists.

			# Read groups can never exist on their own, except for
			# right after deleting the base group.

			succeed;

		} else {
			# Read groups may not be deleted if their base group still exists.
			fail;
		}
	} else {
		uuGroupPolicyCanGroupRemove(uuClientFullName, *groupName, *allowed, *reason);
		if (*allowed == 1) {
			succeed;
		}
	}

	fail;
}

uuGroupPreSudoGroupMemberAdd(*groupName, *userName, *policyKv) {

	*groupToCheck = *groupName

	if (*groupName like "read-*") {
		uuGetBaseGroup(*groupName, *baseGroup);
		uuGroupUserExists(*baseGroup, *userName, false, *isNormalMember);
		if (*isNormalMember) {
			# The user should have been removed from the base group first.
			fail;
		}

		# Allow adding a member to the read- group if the client is allowed to
		# add them to the base group.
		*groupToCheck = *baseGroup;

	} else if (*groupName like "vault-*") {
		uuGetBaseGroup(*groupName, *baseGroup);
		uuGroupUserIsManager(*baseGroup, uuClientFullName, *isManagerInBaseGroup);
		if (*isManagerInBaseGroup && *userName == "rods#$rodsZoneClient") {
			# The only user that can be added to the vault group is rods, and
			# only a manager on the base group can add him.
			succeed;
		} else {
			fail;
		}
	}

	uuGroupPolicyCanGroupUserAdd(
		uuClientFullName(),
		*groupToCheck,
		*userName,
		*allowed, *reason
	);

	if (*allowed == 1) {
		succeed;
	}
	fail;
}

uuGroupPreSudoGroupMemberRemove(*groupName, *userName, *policyKv) {

	# When removing a user from a RO group, allow it if the client would be
	# permitted to remove them from the base group.
	*baseGroup = *groupName;
	if (*groupName like "read-*") {
		uuGetBaseGroup(*groupName, *baseGroup);
	}

	uuGroupPolicyCanGroupUserRemove(
		uuClientFullName,
		*baseGroup,
		*userName,
		*allowed, *reason
	);

	if (*allowed == 1) {
		succeed;
		# Any remaining 'manager' metadata needs to be removed in the
		# postprocessing rule.
	}

	fail;
}

uuGroupPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {

	if (*otherName like "read-*" && *accessLevel == "read") {
		uuGetBaseGroup(*otherName, *baseGroup);
		uuGroupUserIsManager(*baseGroup, uuClientFullName, *isManagerInBaseGroup);

		if (*isManagerInBaseGroup && *baseGroup != *otherName) {
			if (*objPath == "/$rodsZoneClient/home/*baseGroup") {
				# Client wants to give a 'read-' group read access to its base
				# group.
				succeed;
			}
		}
	} else if (*otherName like "datamanager-*" && *accessLevel == "read") {
		*forGroup = *policyKv."forGroup";
		if (*objPath == "/$rodsZoneClient/home/*forGroup") {
			if (*forGroup like regex "(intake|research)-.*") {
				uuGroupUserIsManager(*forGroup, uuClientFullName, *isManagerInGroup);
				uuGroupGetCategory(*forGroup, *category, *_);

				if (*isManagerInGroup && *otherName == "datamanager-*category") {
					# Client wants to give the datamanager group for *category read
					# access to a research/intake directory in *category.
					succeed;
				}

			} else if (*forGroup like "vault-*") {
				uuGetBaseGroup(*forGroup, *baseGroup);
				uuGroupUserIsManager(*baseGroup, uuClientFullName, *isManagerInBaseGroup);
				uuGroupGetCategory(*baseGroup, *category, *_);

				if (*isManagerInBaseGroup && *otherName == "datamanager-*category") {
					# Client wants to give the datamanager group for *category read
					# access to a vault directory in *category.
					succeed;
				}
			}
		}
	} else if (*otherName like "datamanager-*" && *accessLevel == "null") {
		*forGroup = *policyKv."forGroup";
		if (*objPath == "/$rodsZoneClient/home/*forGroup") {
			if (*forGroup like regex "(intake|research)-.*") {
				uuGroupUserIsManager(*forGroup, uuClientFullName, *isManagerInGroup);
				uuGroupGetCategory(*forGroup, *category, *_);

				if (*isManagerInGroup && *otherName != "datamanager-*category") {
					# Client wants to take away read access to a
					# research/intake group from a datamanager group in a
					# different category.
					# Likely because the group has changed categories.
					succeed;
				}

			} else if (*forGroup like "vault-*") {
				uuGetBaseGroup(*forGroup, *baseGroup);
				uuGroupUserIsManager(*baseGroup, uuClientFullName, *isManagerInBaseGroup);
				uuGroupGetCategory(*baseGroup, *category, *_);

				if (*isManagerInBaseGroup && *otherName != "datamanager-*category") {
					# Client wants to take away read access to a vault group
					# from a datamanager group in a different category.
					# Likely because the group has changed categories.
					succeed;
				}
			}
		}
	} else if (*accessLevel == "inherit") {
		*forGroup = *policyKv."forGroup";
		uuGetBaseGroup(*forGroup, *baseGroup);
		uuGroupUserIsManager(*baseGroup, uuClientFullName, *isManagerInBaseGroup);
		if (
			*isManagerInBaseGroup
			&& *objPath == "/$rodsZoneClient/home/*forGroup") {
			# Allow if the client is a manager in the basegroup of *forGroup,
			# and *objPath is *forGroup's home directory.
			# NB: *baseGroup will be "*forGroup" if *forGroup is not a
			# 'read-|vault-' group.
			succeed;
		}
	}

	fail;
}

uuGroupPreSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {

	# MetaSet applies to group properties 'category', 'subcategory',
	# 'description', and 'data_classification'.

	# The 'manager' attributes are managed only with MetaAdd and MetaRemove
	# (see below this rule).

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			if (# We do not use / allow the unit field here.
				*unit == ""
			) {
				if (*attribute == "category") {
					# When setting a group's category, require that the old
					# category name (if any) be passed in *policyKv, so that
					# datamanager-*oldCategory read access can be revoked in
					# the postproc action of metaset.
					uuGroupGetCategory(*objName, *category, *_);
					# (*category will be empty ("") if the group isn't currently in a category)
					if (*category != *policyKv."oldCategory") {
						# This will fail if 'oldCategory' is not given in
						# *policyKv or if it doesn't match the current category.
						fail;
					}
				}
				uuGroupPolicyCanGroupModify(uuClientFullName, *objName, *attribute, *value, *allowed, *reason);
				if (*allowed == 1) {
					succeed;
				}
			}
		}
	}
	fail;
}

uuGroupPreSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) {

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			if (*attribute == "manager" && *unit == "") {
				uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *objName, *value, "manager", *allowed, *reason);
				if (*allowed == 1) {
					succeed;
				}
			}
		}
	}
	fail;
}

uuGroupPreSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) {

	if (*objType == "-u") {
		uuGetUserType(*objName, *targetUserType);
		if (*targetUserType == "rodsgroup") {
			# So, *objName is a group name.

			if (*attribute == "manager" && *unit == "") {
				uuGroupUserExists(*objName, *value, false, *targetUserIsMember);
				if (*targetUserIsMember) {
					# The client is demoting a group member.
					uuGroupPolicyCanGroupUserChangeRole(uuClientFullName, *objName, *value, "normal", *allowed, *reason);
					if (*allowed == 1) {
						succeed;
					}
				} else {
					# The client is removing the manager metadata of a user
					# who is no longer a member of the group.
					# Allow this if the client is a manager in the group.

					uuGroupUserIsManager(*objName, uuClientFullName, *clientIsManager);

					if (*clientIsManager) {
						succeed;
					}
				}
			}
		}
	}
	fail;
}

# }}}
# Postprocessing rules. {{{

#uuPostSudoUserAdd(*userName, *initialAttr, *initialValue, *initialUnit, *policyKv) { }
#uuPostSudoUserRemove(*userName, *policyKv) { }

uuPostSudoGroupAdd(*groupName, *initialAttr, *initialValue, *initialUnit, *policyKv) {

	if (*groupName like "read-*") {
		# No postprocessing required for ro groups.
		succeed;
	}

	if (*groupName like "vault-*") {
		# No postprocessing for vault groups here - but see below for actions
		# taken after automatic creation of vault groups.

	} else {
		# This is a group manager managed group (i.e. 'research-', 'grp-', 'intake-', 'priv-', 'datamanager-').
		# Add the creator as a member.

		errorcode(msiSudoGroupMemberAdd(*groupName, uuClientFullName, ""));

		# Perform group prefix-dependent actions (e.g. create vaults for intake/research groups).

		if (*groupName like regex "(intake|research)-.*") {

			# Create a corresponding RO group.

			uuChop(*groupName, *_, *baseName, "-", true);
			*roGroupName = "read-*baseName";
			msiSudoGroupAdd(*roGroupName, "", "", "", "");

			# Give the RO group read access.
			msiSudoObjAclSet("recursive", "read", *roGroupName, "/$rodsZoneClient/home/*groupName", "");

			# Create vault group.

			uuChop(*groupName, *_, *baseName, "-", true);
			*vaultGroupName = "vault-*baseName";
			msiSudoGroupAdd(*vaultGroupName, "", "", "", "");
			# Add rods to the vault group.
			msiSudoGroupMemberAdd(*vaultGroupName, "rods#$rodsZoneClient", "");

		} else if (*groupName like "datamanager-*") {

			# Give the newly created datamanager group read access to all
			# existing intake/research home dirs and vaults in its category.

			*category = *policyKv."category";

			foreach (
				# Iterate over groups within the same category.
				*row in
				SELECT USER_GROUP_NAME
				WHERE  USER_TYPE            = 'rodsgroup'
				  AND  META_USER_ATTR_NAME  = 'category'
				  AND  META_USER_ATTR_VALUE = '*category'
			) {
				# Filter down to intake/research groups and get their vault groups.
				*catGroup = *row."USER_GROUP_NAME";
				if (*catGroup like regex "(intake|research)-.*") {

					*aclKv."forGroup" = *catGroup;
					msiSudoObjAclSet("recursive", "read", *groupName, "/$rodsZoneClient/home/*catGroup", *aclKv);

					uuChop(*catGroup, *_, *catGroupBase, "-", true);
					*vaultGroupName = "vault-*catGroupBase";

					uuGroupExists(*vaultGroupName, *vaultExists);
					if (*vaultExists) {
						*aclKv."forGroup" = *vaultGroupName;
						msiSudoObjAclSet("recursive", "read", *groupName, "/$rodsZoneClient/home/*vaultGroupName", *aclKv);
					}
				}
			}
		}

		# Set group manager-managed group metadata.
		#
		# Note: Setting the category of an intake/research group will trigger
		# an ACL change: The datamanager group in the category, if it exists
		# will get read access to this group an its accompanying vault.
		# See uuPostSudoObjMetaSet.

		*categoryKv.'oldCategory' = "";
		errorcode(msiSudoObjMetaSet(*groupName, "-u", "category",      *policyKv."category",    "", *categoryKv));
		errorcode(msiSudoObjMetaSet(*groupName, "-u", "subcategory",   *policyKv."subcategory", "", ""));

		*description = if *policyKv."description" != "" then *policyKv."description" else ".";
		errorcode(msiSudoObjMetaSet(*groupName, "-u", "description",   *description, "", ""));

		if (*policyKv."data_classification" != "") {
			errorcode(msiSudoObjMetaSet(*groupName, "-u", "data_classification", *policyKv."data_classification", "", ""));
		}
	}

	# Put the group name in the policyKv to assist the acl policy.
	*aclKv."forGroup" = *groupName;

	# Enable inheritance for the new group.
	msiSudoObjAclSet("recursive", "inherit", "", "/$rodsZoneClient/home/*groupName", *aclKv);
}

uuPostSudoGroupRemove(*groupName, *policyKv) {
	if (*groupName like regex "(intake|research)-.*") {
		# This is a group manager managed group with a read-only counterpart.
		# Clean up the read-only shadow group.

		uuChop(*groupName, *_, *baseName, "-", true);
		*roGroupName = "read-*baseName";
		msiSudoGroupRemove(*roGroupName, "");

		# Remove the vault group if it is empty.
		# We need a msiExecCmd here because the user removing this
		# research/intake group does not necessarily have read access to the
		# vault, and thus cannot check whether the vault is empty.
		# This will also remove the orphan revision collection, if it exists.
		uuGroupRemoveOrphanVaultIfEmpty("vault-*baseName");
	}
}

#uuPostSudoGroupMemberAdd(*groupName, *userName, *policyKv) { }

uuPostSudoGroupMemberRemove(*groupName, *userName, *policyKv) {

	# Remove the user's manager attr on this group, if it exists.

	# The manager attribute only grants a user group manager rights if they are
	# also a member of the group. As such it is not a critical error if this
	# call fails.
	errorcode(msiSudoObjMetaRemove(*groupName, "-u", "", "manager", *userName, "", ""));
}

#uuPostSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) { }

uuPostSudoObjMetaSet(*objName, *objType, *attribute, *value, *unit, *policyKv) {
	# Update datamanager ACLs on a group directory that changes categories.
	ON (
		*objType == "-u"
		# vault- and read- groups don't define their own category attribute.
		&& *objName like regex "(intake|research)-.*"
		&& *attribute == "category"
	) {
		# Make sure it's actually a group.
		uuGroupExists(*objName, *isGroup);
		if (!*isGroup) { succeed; }

		# As enforced by the preproc rule for metaset, an oldCategory value
		# must be defined in the policyKv that matches the original category
		# before this operation. We use this to determine the datamanager group
		# whose read access must be revoked.
		*oldCategory = *policyKv.'oldCategory';
		*newCategory = *value;

		# Nothing to do.
		if (*oldCategory == *newCategory) { succeed; }

		# Take read access away from the datamanager group of the old category, if it exists.
		if (*oldCategory != "") {
			*oldDatamanagerGroupName = "datamanager-*oldCategory";
			uuGroupExists(*oldDatamanagerGroupName, *oldCategoryHasDatamanagerGroup);
			if (*oldCategoryHasDatamanagerGroup) {
				*kv.'forGroup' = *objName;
				msiSudoObjAclSet("recursive", "null", *oldDatamanagerGroupName, "/$rodsZoneClient/home/*objName", *kv);

				uuChop(*objName, *_, *baseName, "-", true);
				*vaultGroupName = "vault-*baseName";
				*kv.'forGroup' = *vaultGroupName;
				msiSudoObjAclSet("recursive", "null", *oldDatamanagerGroupName, "/$rodsZoneClient/home/*vaultGroupName", *kv);
			}
		} # else, it's a new group that didn't yet have an assigned category.

		*datamanagerGroupName = "datamanager-*newCategory";
		uuGroupExists(*datamanagerGroupName, *datamanagerGroupExists);
		if (*datamanagerGroupExists) {
			# The destination category has a datamanager group, give our new
			# datamanager overlords read access to our home directory and the accompanying vault.
			*kv.'forGroup' = *objName;
			msiSudoObjAclSet("recursive", "read", *datamanagerGroupName, "/$rodsZoneClient/home/*objName", *kv);

			uuChop(*objName, *_, *baseName, "-", true);
			*vaultGroupName = "vault-*baseName";
			*kv.'forGroup' = *vaultGroupName;
			msiSudoObjAclSet("recursive", "read", *datamanagerGroupName, "/$rodsZoneClient/home/*vaultGroupName", *kv);
		}
	}
}

#uuPostSudoObjMetaAdd(*objName, *objType, *attribute, *value, *unit, *policyKv) { }
#uuPostSudoObjMetaRemove(*objName, *objType, *wildcards, *attribute, *value, *unit, *policyKv) { }

# }}}
