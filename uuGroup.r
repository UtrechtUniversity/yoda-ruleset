# \file
# \brief functions for group management and group queries
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#test() {
#	*user = "ron";
#	*group = "yoda";
#	uuGroupUserExists(*group, *user, *membership);
#	writeLine("stdout","*user membership of group *group : *membership");
#}

# \brief uuGroupUserExists check if user if member of a group
# 
# \param[in] group        name of the irods group
# \param[in] user         name of the irods user
# \param[out] membership  true if user is a member of this group
#

uuGroupUserExists(*group, *user, *membership) {
	*membership = false;
	foreach (*row in SELECT USER_NAME WHERE USER_GROUP_NAME=*group) {
		msiGetValByKey(*row, "USER_NAME", *member);
		if (*member == *user) {
			*membership = true;
		}
	}
}
#input *group="grp-yc-intake"
#output ruleExecOut
