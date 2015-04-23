# \file
# \brief     UU - List functions.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# \brief Check if a list contains a certain string value.
#
# \param value
# \param list
# \param inList
#
uuListContains(*value, *list, *inList) {
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
# \param pattern
# \param list
# \param inList
#
uuListMatches(*pattern, *list, *inList) {
	*inList = false;
	foreach (*item in *list) {
		if (*item like regex *pattern) {
			*inList = true;
			break;
		}
	}
}
