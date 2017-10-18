# \file
# \brief File statistics functions
#			Functions in this file extract statistics from files
#			and collections
# \author Jan de Mooij
# \author Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#

# \brief iiFileCount 		Obtain a count of all files in a collection
#
# \param[in] path 		The full path to a collection (not a file). This
#				is the COLL_NAME.
# \param[out] totalSize 	Integer giving the sum of the size of all
#				the objects in the collection in bytes
# \param[out] dircount		The number of child directories in this collection
#				this number is determined recursively, so this does
#				include all subdirectories and not only those directly
#				under the given collection
# \param[out] filecount 	The total number of files in this collection. This
#				number is determined recursively, so this does include
#				all subfiles and not just those directly under the
#				given collection.
# \param[out] modified      Unix timestamp of the modify datetime of the file that
#                           was modified last
iiFileCount(*path, *totalSize, *dircount, *filecount, *modified) {
    *dircount = 0;
    *filecount = 0;
    *totalSize = 0;
    *data_modified = 0;
    *coll_modified = 0;

    foreach (*row in SELECT DATA_ID WHERE COLL_NAME like "*path%") {
        *filecount = *filecount + 1;
    }

    foreach (*row in SELECT DATA_ID, DATA_SIZE, DATA_MODIFY_TIME
                     WHERE COLL_NAME like "*path%") {
        *totalSize = *totalSize + int(*row."DATA_SIZE");
	if (*data_modified < int(*row."DATA_MODIFY_TIME")) {
	    *data_modified = int(*row."DATA_MODIFY_TIME");
	}
    }

    foreach (*row in SELECT COLL_ID, COLL_MODIFY_TIME
                     WHERE COLL_NAME like "*path%") {
        *dircount = *dircount + 1;
	if (*coll_modified < int(*row."COLL_MODIFY_TIME")) {
	    *coll_modified = int(*row."COLL_MODIFY_TIME");
	}
    }

    *modified = str(max(*data_modified, *coll_modified));
}

# \brief iiCollectionGroupName    return the name of the group a collection belongs to
# \param[in] path
# \param[out] groupName
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
		# No results found. Not a group folder
		failmsg(-808000, "*path does not belong to a research or intake group or is not available to current user");
	}
}

# \brief iiCollectionGroupNameAndUserType
# \param[in] path
# \param[out] groupName
# \param[out] userType
# \param[out] isDatamanager
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
