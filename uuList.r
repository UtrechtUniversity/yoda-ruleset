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

# \brief Return the index of a value within a list or -1 when not in list
#
# \param[in] list
# \param[in] value
# \param[out] indexOf
#
uuListIndexOf(*list, *value, *indexOf) {
	*indexOf = 0;
	foreach (*item in *list) {
		if (*item == *value) {
			break;
		}
		*indexOf = *indexOf + 1;
	}
	if (*indexOf == size(*list)) {
		*indexOf = -1;
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


# \brief inlist         Returns true if a value is found in a list. Useful for inside expressions. Only works when the
#                       list elements and the value have the same type
# \param[in] val	A value
# \param[in] lst	A list of values
# \returnvalue	true when value in list, false otherwise
uuinlist(*val, *lst) = if size(*lst) == 0  then false else uuheadinlist(*val, *lst)

#\brief headinlist	Helper function for in list. Checks the head of the list for value. The list is iterated using
#                       mutual recursion.
uuheadinlist(*val, *lst) = if hd(*lst) == *val then true else uuinlist(*val, tl(*lst))

