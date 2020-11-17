# \file      uuList.r
# \brief     List functions.
# \author    Chris Smeele
# \author    Paul Frederiks
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Check if a list contains a certain string value.
#
# \param list
# \param value
# \param inList
#
uuListContains(*list, *value, *inList) {
	*inList = false;
	foreach (*item in *list) {
		if (*item == *value) {
			*inList = true;
			break;
		}
	}
}

# \brief Check if an item in list matches a certain regex.
#
# \param list
# \param pattern
# \param inList
#
uuListMatches(*list, *pattern, *inList) {
	*inList = false;
	foreach (*item in *list) {
		if (*item like regex *pattern) {
			*inList = true;
			break;
		}
	}
}

# \brief Join a list.
#
# \param[in]  delimiter
# \param[in]  list
# \param[out] str contains all elements in `list`, separated by `delimiter`
#
uuJoin(*delimiter, *list, *str) {
	*str = "";
	foreach (*item in *list) {
		if (strlen(*str) > 0) {
			*str = *str ++ *delimiter ++ *item;
		} else {
			*str = *item;
		}
	}
}

# \brief Return a reversed list
# \param[in] list to reverse
# \returnvalue reversed list
uuListReverse(*lst) {
	*newlst = list();
	foreach(*el in *lst){
		*newlst = cons(*el, *newlst);
	}
	*newlst;
}
