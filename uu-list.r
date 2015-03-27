# \file
# \brief     UU - (Key-value) list functions.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.txt.

# \brief Clears a kv-list's contents.
#
# \param kvList
#
uuKvClear(*kvList) {
	#*empty."." = ".";
	#*kvList = *empty;
	*kvList."." = ".";
	foreach (*key in *kvList) {
		*kvList.*key = ".";
	}
}

# \brief Clone a key-value list.
#
# The destination list is cleared before copying.
#
# \param[in]  source
# \param[out] dest
#
uuKvClone(*source, *dest) {
	uuKvClear(*dest);
	foreach (*key in *source) {
		*dest.*key = *source.*key;
	}
}

# \brief Merge two key-value lists.
#
# list1 is copied to result, and any key in list2 that was not present in list1
# is added to the result.
#
# \param[in]  list1
# \param[in]  list2
# \param[out] result
#
uuKvMerge(*list1, *list2, *result) {
	uuKvClear(*result);
	uuKvClone(*list1, *result);

	foreach (*key in *list2) {
		*bool = false;
		uuKvExists(*result, *key, *bool)
		if (!*bool) {
			*result.*key = *list2.*key;
		}
	}
}

# \brief Check if a key exists in a key-value list.
#
# \param[in]  kvList
# \param[in]  key
# \param[out] bool
#
uuKvExists(*kvList, *key, *bool) {
	#if (errorcode(*kvList.*key) == 0) {
		*bool = (*kvList.*key != '.');
	#} else {
	#	*bool = false;
	#}
}
