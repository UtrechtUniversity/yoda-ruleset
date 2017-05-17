# \file
# \brief Sudo microservices policy implementations to enable datamanager control of vault process
# \author Paul Frederiks
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \licens GPLv3 LICENSE

# \brief iiDatamanagerPreSudoObjAclSet
iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	if (*recursive == 0 && (*accesslevel == "write" || *accessLevel == "read")) {
		*actor = uuClientFullName;
		iiCanDatamanagerAclSet(*objPath, uuClientFullName, *allowed, *reason);
		if (*allowed) {
			succeed;
		}
	}
	fail;
}


# \brief iiCanDatamanagerAclSet
iiCanDatamanagerAclSet(*objPath, *actor, *allowed, *reason) {
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
		*reason = "A datamanager has no permission to alter *objPath with status '*folderStatus'";
	}
}
