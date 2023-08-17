
# \file      iiDatamanagerPolicies.r
# \brief     Sudo microservices policy implementations to enable datamanager control of vault process.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2022, Utrecht University. All rights reserved.
# \licens    GPLv3 see LICENSE.


# This policy override enables the datamanager to manage ACL's in the vault
# it's signature is defined in the sudo microservice
# The implementation is redirected to iiDatamanagerPreSudoObjAclSet in iiDatamanagerPolicies.r
acPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	ON (*otherName like regex "(datamanager|research|deposit|read)-.*") {
		iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv);
	}
}

# \brief This rule should be called from acPreSudoObjAclSet on sudo ACL set actions.
#
# \param[in] recursive
# \param[in] accessLevel
# \param[in] otherName
# \param[in] objPath
# \param[in] policyKv
#
iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	# Initially current user will be set as actor.
	# If policyKv holds another, then that actor will override.
	*actor = uuClientFullName;
	foreach(*key in *policyKv) {
		if (*key == "actor") {
			*actor = *policyKv.actor
			break;
		}
	}

	iiCanDatamanagerAclSet(*objPath, *actor, *otherName, *recursive, *accessLevel, *allowed, *reason);
	writeLine("serverLog", "iiDatamanagerPreSudoObjAclSet: *reason");
	if (*allowed) {
		succeed;
	}
	fail;
}

# \brief Determine the datamanager group belonging to a vault group as vault
#        groups do not have metadata on the category themselves.
#
# \param[in] vaultGroup         group name starting with vault-
# \param[out] datamanagerGroup  group name of the datamanager group belonging to the category of the research group
#                               associated with the vault
#
iiDatamanagerGroupFromVaultGroup(*vaultGroup, *datamanagerGroup) {
	uuGetBaseGroup(*vaultGroup, *baseGroup);
	uuGroupGetCategory(*baseGroup, *category, *subcategory);
	*datamanagerGroup = "datamanager-*category";
	uuGroupExists(*datamanagerGroup, *datamanagerExists);
	if (!*datamanagerExists) {
		*datamanagerGroup = "";
	}
}

# \brief Check if the requester is allowed to change ACL's in the vault.
#
# \param[in] objPath
# \param[in] actor
# \param[in] otherName
# \param[in] recursive
# \param[in] accessLevel
# \param[out] allowed
# \param[out] reason
#
iiCanDatamanagerAclSet(*objPath, *actor, *otherName, *recursive, *accessLevel, *allowed, *reason) {
	# When the datamanager needs write/read access to the root of a vault package this rule is run
	on (*otherName like "datamanager-*" && *objPath like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++".*") {
		writeLine("serverLog", "iiCanDatamanagerAclSet: <*actor> wants to obtain <*accessLevel> on <*objPath>");
		if (*accessLevel != "write" && *accessLevel != "read") {
			*allowed = false;
			*reason = "A datamanager can only obtain or revoke write access for the datamanager group to a vault package";
			succeed;
		}

		msiGetObjType(*objPath, *objType);
		if (*objType != "-c") {
			*allowed = false;
			*reason = "A datamanager can only change permissions on collections in the vault";
			succeed;
		}

		uuGroupExists(*otherName, *datamanagerExists);
		if (!*datamanagerExists) {
			*allowed = false;
			*reason = "User is not a datamanager or *otherName does not exists.";
			succeed;
		}
		uuGroupGetMemberType(*otherName, *actor, *userTypeIfDatamanager);
		if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
			*allowed = true;
			*reason = "User is a datamanager.";
		} else {
			*allowed = false;
			*reason = "User is not a datamanager.";
			succeed;
		}

	}

	# When a datamanager wants to grant or revoke read access for a research or read group in the vault, this rule will run
	on (*objPath like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++".*") {
		writeLine("serverLog", "iiCanDatamanagerAclSet: <*actor> wants to set <*accessLevel> for <*otherName> on <*objPath>");
		if (*accessLevel != "read" && *accessLevel != "null") {
			*allowed = false;
			*reason = "A datamanager can only grant write or read access or revoke access in the vault.";
			succeed;
		}

		uuChop(*otherName, *_, *baseGroupName, "-", true);
		if (*otherName == IIGROUPPREFIX ++ *baseGroupName || *otherName == "deposit-" ++ *baseGroupName || *otherName == "read-" ++ *baseGroupName) {
			if (*otherName == "deposit-" ++ *baseGroupName) {
				uuGroupGetCategory("deposit-" ++ *baseGroupName, *category, *subcategory);
			} else {
				uuGroupGetCategory(IIGROUPPREFIX ++ *baseGroupName, *category, *subcategory);
				uuGroupExists("research-*baseGroupName", *researchExists);
				if (!*researchExists) {
					*allowed = false;
					*reason = "Cannot grant or revoke read access, research group *category does not exist.";
					succeed;
				}
			}

			uuGroupExists("datamanager-*category", *datamanagerExists);
			if (!*datamanagerExists) {
				*allowed = false;
				*reason = "User is not a datamanager or no datamanager exists.";
				succeed;
			}
			uuGroupGetMemberType("datamanager-*category", *actor, *userTypeIfDatamanager);
			if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
				*allowed = true;
				*reason = "User is a datamanager of category *category.";
			} else {
				*allowed = false;
				*reason = "User is not a datamanager.";
				succeed;
			}
		} else {
			*allowed = false;
			*reason = "Only research groups can be granted read access to the vault";
			succeed;
		}

		*vaultGroupName = IIVAULTPREFIX ++ *baseGroupName;
		*pathElems = split(*objPath, "/");
		if (size(*pathElems) < 4) {
		    *allowed = false;
		    *reason = "*objPath is not a datapackage in the vault.";
		} else if (elem(*pathElems, 2) != *vaultGroupName) {
			*allowed = false;
			*reason = "*objPath is not part of *vaultGroupName";
		}
	}

	# when a status transition in the research area is invoked by the datamanager, he needs temporary write access to change the folder status
	on (*objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {

		if (*accessLevel == "inherit" || *accessLevel == "own") {
			*allowed = false;
			*reason = "Cannot grant own or inherit to *objPath";
			succeed;
		}

		*groupName = "";
		rule_collection_group_name(*objPath, *groupName);
		uuGroupGetCategory(*groupName, *category, *subcategory);
		if (*otherName == "datamanager-*category") {
			uuGroupGetMemberType(*otherName, *actor, *userTypeIfDatamanager);
			if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
				*allowed = true;
				*reason = "User is a datamanager of category *category.";
			} else {
				*allowed = false;
				*reason = "User is not a datamanager.";
			}
		} else {
			*allowed = false;
			*reason = "Permission can only be granted to the datamanager-*category group, not *otherName.";
		}
	}

	# fallback to prevent users defining and using there own iiCanDatamanagerAclSet. This is also reached when the frontend requests a status change it is not allowed to
	on (true) {
		*allowed = false;
		*reason = "Current status of folder *objPath is not 'submitted', 'accepted' or 'rejected'. Therefore the requested action can not be completed as a datamanager.";
	}
}
