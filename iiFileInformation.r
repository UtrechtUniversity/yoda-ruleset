# \file      iiFileInformation.r
# \brief     File statistics functions
#            Functions in this file extract statistics from files and collections.
# \author    Jan de Mooij
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2016-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.
#

# \brief Return the name of the group a collection belongs to.
#
# \param[in]  path
# \param[out] groupName
#
iiCollectionGroupName(*path, *groupName) {
	*isfound = false;
	*groupName = "";
	foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
		*id = *accessid.COLL_ACCESS_USER_ID;
		foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id) {
				*groupName = *group.USER_GROUP_NAME;
		}
		if (*groupName like regex "(research|intake)-.*") {
			*isfound = true;
			break;
		}
	}

	if (!*isfound) {
		foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
			*id = *accessid.COLL_ACCESS_USER_ID;
			foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id) {
					*groupName = *group.USER_GROUP_NAME;
			}
			if (*groupName like regex "(datamanager|vault)-.*") {
				*isfound = true;
				break;
			}
		}
	}
	if (!*isfound){
		# No results found. Not a group folder
		writeLine("serverLog", "*path does not belong to a research or intake group or is not available to current user");
	}
}

# \brief iiCollectionGroupNameAndUserType
#
# \param[in]  path
# \param[out] groupName
# \param[out] userType
# \param[out] isDatamanager
#
iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager) {
	iiCollectionGroupName(*path, *groupName);
	uuGroupGetMemberType(*groupName, uuClientFullName, *userType);

	uuGroupGetCategory(*groupName, *category, *subcategory);
	uuGroupGetMemberType("datamanager-" ++ *category, uuClientFullName, *userTypeIfDatamanager);
	if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
		*isDatamanager = true;
	} else {
		*isDatamanager = false;
	}
}
