# \file
# \brief This file contains rules related to metadata
#                       to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief GetAvailableValuesForKeyLike Returns list of values that exist in the
# 										icat database for a certain key, which
# 										are like a certain value
#
# \param[in] *key 						Key to look for
# \param[in] *searchString 				String that should be a substring of the
# 										returned values
# \param[in] *isCollection 				Wether to look in collection or data 
# \param[out] *values 					List of possible values for the given key
# 										where the given search string is a substring of
uuIiGetAvailableValuesForKeyLike(*key, *searchString, *isCollection, *values){
	*values = list();

	if(*isCollection){
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE 
			META_COLL_ATTR_NAME like '*key' AND
			META_COLL_ATTR_VALUE like '%*searchString%') {
			writeLine("stdout", *row.META_COLL_ATTR_VALUE);
			*values = cons(*row.META_COLL_ATTR_VALUE,*values);
			writeLine("serverLog", *row.META_COLL_ATTR_VALUE);
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE 
			META_DATA_ATTR_NAME like '*key' AND
			META_DATA_ATTR_VALUE like '%*searchString%') {
			*values = cons(*row.META_DATA_ATTR_VALUE,*values);
		}
	}
}

