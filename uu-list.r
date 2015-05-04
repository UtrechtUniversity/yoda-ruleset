# \file
# \brief     UU - List functions.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

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

# \brief Filter a list using a pattern.
#
# \param[in]  list
# \param[in]  pattern
# \param[in]  isRegex if true, pattern is treated like a regular expression instead of a plain string
# \param[in]  include if true, includes matching entries. excludes matches otherwise.
# \param[out] newList
#
uuListFilter(*list, *pattern, *isRegex, *include, *newList) {
	*separator = "\n\n";
	*newListString = "";

	foreach (*item in *list) {
		*matches = false;
		if (*isRegex) {
			*matches = *item like regex *pattern;
		} else {
			*matches = *item == *pattern;
		}
		if (*matches) {
			if (*include) {
				*newListString = *newListString ++ *separator ++ *item;
			}
		} else if (!*include) {
			*newListString = *newListString ++ *separator ++ *item;
		}
	}

	*newListString = triml(*newListString, *separator);
	*newList       = split(*newListString, *separator);
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
