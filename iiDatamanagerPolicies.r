# \file
# \brief Sudo microservices policy implementations to enable datamanager control of vault process
# \author Paul Frederiks
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved
# \licens GPLVv3 LICENSE

iiDatamanagerPreSudoObjAclSet(*recursive, *accessLevel, *otherName, *objPath, *policyKv) {
	*actor = *policyKv.actor;
	iiFolderStatus(*objPath, *folderStatus);
	writeLine("serverLog", "iiDatamanagerPreSudoObjAclSet: folderStatus = *folderStatus");
	if (*folderStatus == SUBMITTED || *folderStatus == ACCEPTED || *folderStatus == REJECTED) {
		iiCollectionGroupName(*objPath, *groupName);
		uuGroupGetCategory(*groupName, *category, *subcategory);
		writeLine("serverLog", "iiDatamanagerPreSudoObjAclSet: *category; *otherName");
		if (*otherName == "datamanager-*category") {
			
			uuGroupGetMemberType(*otherName, *actor, *userTypeIfDatamanager);
			writeLine("serverLog", "iiDatamanagerPreSudoObjAclSet: *actor - *userTypeIfDatamanager");
			if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
				
				succeed;
			}
		}
	}
	fail;
}
