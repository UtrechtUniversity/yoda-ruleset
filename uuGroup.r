# \file
# \brief functions for group management and group queries
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

#test() {
#	*user = "bert#tsm";
#   *group = "yoda";
#	uuGroupUserExists(*group, *user, *membership);
#	writeLine("stdout","*user membership of group *group : *membership");
#	uuGroupMemberships(*user, *groups);
#	writeLine("stdout","allgroups=*groups");
#	foreach (*grp in split(*groups,',')){
#		writeLine("stdout","grp = *grp");
#	}
#}

# \brief uuGetUserAndZone extract username and zone in separate fields
# 
# \param[in] user       name of the irods user
#                       username can optionally include zone ('user#zone')
#                       default is to use the local zone
# \param[out] userName  name of user exclusing zone information
# \param[out] userZone  name of the zone of the user
#
uuGetUserAndZone(*user,*userName,*userZone) {
	*userAndZone = split(*user, "#");
	*userName = elem(*userAndZone,0);
	if (size(*userAndZone) > 1) {
		*userZone = elem(*userAndZone,1);
	} else {
		*userZone = $rodsZoneClient;
	}
}
# \brief uuGroupUserExists check if user if member of a group
# 
# \param[in] group        name of the irods group
# \param[in] user         name of the irods user
#                         username can optionally include zone ('user#zone')
#                         default is to use the local zone
# \param[out] membership  true if user is a member of this group
#
uuGroupUserExists(*group, *user, *membership) {
	*membership = false;
	uuGetUserAndZone(*user,*userName,*userZone);
	foreach (*row in SELECT USER_NAME,USER_ZONE WHERE USER_GROUP_NAME=*group) {
		msiGetValByKey(*row, "USER_NAME", *member);
		msiGetValByKey(*row, "USER_ZONE", *memberZone);
		if ((*member == *userName) && (*memberZone == *userZone)) {
			*membership = true;
		}
	}
}

# \brief uuGroupMemberships lists all groups the user belongs to
#
# \param[in] user     name of the irods user
#                     username can optionally include zone ('user#zone')
#                     default is to use the local zone
# \param[out] groups  comma separated list of groupnames
#
uuGroupMemberships(*user, *groups) {
	uuGetUserAndZone(*user,*userName,*userZone);
	*groups="";
	foreach (*row in SELECT USER_GROUP_NAME 
				WHERE USER_NAME = '*userName' AND USER_ZONE = '*userZone') {
		msiGetValByKey(*row,"USER_GROUP_NAME",*group);
		*groups = "*groups,*group";
	}
	*groups=triml(*groups,",");
}

# \brief Get a list of group categories.
#
# \param[out] categories a list of category names
#
uuGroupGetCategories(*categories) {
	*categoriesString = "";
	foreach (
		*category
		in SELECT META_COLL_ATTR_VALUE
		   WHERE  COLL_PARENT_NAME     = '/$rodsZoneClient/group'
		     AND  META_COLL_ATTR_NAME  = 'category'
	) {
		*categoriesString = "*categoriesString," ++ *category."META_COLL_ATTR_VALUE";
	}
	*categories = split(*categoriesString, ",");
}

# \brief Get a list of group subcategories.
#
# \param[in]  category      a category name
# \param[out] subcategories a list of subcategory names
#
uuGroupGetSubcategories(*category, *subcategories) {
	*subcategoriesString = "";
	foreach (
		*categoryGroupColl
		in SELECT COLL_NAME
		   WHERE  COLL_PARENT_NAME     = '/$rodsZoneClient/group'
		     AND  META_COLL_ATTR_NAME  = 'category'
		     AND  META_COLL_ATTR_VALUE = '*category'
	) {
		*collName = *categoryGroupColl."COLL_NAME";
		foreach (
			*subcategory
			in SELECT META_COLL_ATTR_VALUE
			   WHERE  COLL_NAME            = '*collName'
			     AND  META_COLL_ATTR_NAME  = 'subcategory'
		) {
			*subcategoryName = *subcategory."META_COLL_ATTR_VALUE";
			if (!(
				   (*subcategoriesString == *subcategoryName)
				|| (*subcategoriesString like "*,*subcategoryName")
				|| (*subcategoriesString like   "*subcategoryName,*")
				|| (*subcategoriesString like "*,*subcategoryName,*")
			)) {
				if (strlen(*subcategoriesString) > 0) {
					*subcategoriesString = "*subcategoriesString,*subcategoryName";
				} else {
					*subcategoriesString = *subcategoryName;
				}
			}
		}
	}
	*subcategories = split(*subcategoriesString, ",");
}

#input *group="grp-yc-intake"
#output ruleExecOut
