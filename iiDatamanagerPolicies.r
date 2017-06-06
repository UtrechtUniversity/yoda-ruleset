# \file
# \brief Sudo microservices policy implementations to enable datamanager control of vault process
# \author Paul Frederiks
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \licens GPLv3 LICENSE

# \brief iiDatamanagerPreSudoObjAclSet
iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	*actor = *policyKv.actor;
	iiCanDatamanagerAclSet(*objPath, *actor, *otherName, *recursive, *accessLevel, *allowed, *reason);
	writeLine("serverLog", "iiDatamanagerPreSudoObjAclSet: *reason");
	if (*allowed) {
		succeed;
	}
	fail;
}


# \brief iiCanDatamanagerAclSet
iiCanDatamanagerAclSet(*objPath, *actor, *otherName, *recursive, *accessLevel, *allowed, *reason) {
	
	on (*objPath like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++".*") {
		writeLine("serverLog", "iiCanDatamanagerAclSet: <*actor> wants to set <*accessLevel> for <*otherName> on <*objPath>");
		if (*accessLevel != "read" && *accessLevel != "null") {
			*allowed = false;
			*reason = "A datamanager can only grant read access or revoke access in the vault.";
			succeed;
		}

		*baseGroupName = triml(*otherName, IIGROUPPREFIX);	
		if (*otherName == IIGROUPPREFIX ++ *baseGroupName || *otherName == "read-" ++ *baseGroupName) {
			uuGroupGetCategory(IIGROUPPREFIX ++ *baseGroupName, *category, *subcategory);
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
       
	on (*objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {

		if (*recursive == 1 || *accessLevel == "own") {
			*allowed = false;
			*reason = "Cannot grant own or inherit to *objPath";
			succeed;
		}
		iiFolderStatus(*objPath, *folderStatus);
		if (*folderStatus == SUBMITTED || *folderStatus == ACCEPTED || *folderStatus == REJECTED) {
			iiCollectionGroupName(*objPath, *groupName);
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
		} else {
			*allowed = false;
			if (*folderStatus == FOLDER) {
				*reason = "A datamanager has no permission to alter *objPath.";
			} else {
				*reason = "A datamanager has no permission to alter *objPath with status '*folderStatus'.";
			}
		}
	} 
	on (true) {
		*allowed = false;
		*reason = "Datamanager can only manage research groups or the vault";
	}
}
