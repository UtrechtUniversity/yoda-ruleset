# \file
# \brief This file contains rules for reading, adding or deleting metadata
# 			from objects
#                       to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief associateKeyWithObject  Associates a value to a key that may
# 									or may not already be associated
#									with that object. The value is added
#									to the already existing metadata
#
# \param[in] key 			Key to be associated
# \param[in] value 			The value for the key
# \param[in] object 		Object the key/value pair should be associated to
# \param[in] isCollection 	Bool indicating wether target object is collection
# \param[in] recursive 		Bool, indicating wether all children should have
#								the key/value pair associated as well, if the
# 								current object is a collection
# \param[out] status 		Integer indicating succes. Non-zero is fail
uuIiAssociateKeyWithObject(*key, *value, *object, *isCollection, *recursive, *status) {
	if(*recursive) {
		writeLine("stdout", "implement with tree walk");
	} else {
		msiString2KeyValPair("*key=*value", *kvPair);
		if(*isCollection) {
			*t = "-C"
		} else {
			*t = "-d"
		}
		*status = errorcode(
			msiAssociateKeyValuePairsToObj(*kvPair, *object, *t)
		);
	}
}

# \brief replaceValueForKey 	Removes existing values for the key from the
# 								object if the key already exists, then adds
# 								the key value pair
#
# \param[in] key 			Key to be associated
# \param[in] value 			The value for the key
# \param[in] object 		Object the key/value pair should be associated to
# \param[in] isCollection 	Bool indicating wether target object is collection
# \param[in] recursive 		Bool, indicating wether all children should have
#								the key/value pair associated as well, if the
# 								current object is a collection
# \param[out] status 		Integer indicating succes. Non-zero is fail
uuIiReplaceValueForKey(*key, *value, *object, *isCollection, *recursive, *status) {
	if(*recursive) {
		writeLine("stdout", "implement with tree walk");
	} else {
		msiString2KeyValPair("*key=*value", *kvPair);
		if(*isCollection) {
			*t = "-C"
		} else {
			*t = "-d"
		}
		*status = errorcode(
			msiSetKeyValuePairsToObj(*kvPair, *object, *t)
		);
	}
}

# \brief removeKeyValueFromObject 	Removes a key/value pair from an object, 
# 									if it exists
#
# \param[in] key 			Key to be removed
# \param[in] value 			The value for the key which is to be removed
# \param[in] object 		Object the key/value pair should be removed from
# \param[in] isCollection 	Bool indicating wether target object is collection
# \param[in] recursive 		Bool, indicating wether all children should have
#								the key/value pair removed as well, if the
# 								current object is a collection
# \param[out] status 		Integer indicating succes. Non-zero is fail
uuIiRemoveKeyValueFromObject(*key, *value, *object, *isCollection, *recursive, *status) {
	if(*recursive) {
		writeLine("stdout", "implement with tree walk");
	} else {
		msiString2KeyValPair("*key=*value", *kvPair);
		if(*isCollection) {
			*t = "-C"
		} else {
			*t = "-d"
		}
		*status = errorcode(
			msiRemoveKeyValuePairsFromObj(*kvPair, *object, *t)
		);
	}
}

# \brief removeKeyFromObject 	Removes all values for the given key 
# 								from the given object
#
# \param[in] key 			Key to be associated
# \param[in] object 		Object the key should be removed from
# \param[in] isCollection 	Bool indicating wether target object is collection
# \param[in] recursive 		Bool, indicating wether all children should have
#								the key removed as well, if the
# 								current object is a collection
# \param[out] status 		Integer indicating succes. Non-zero is fail
uuIiRemoveKeyFromObject(*key, *object, *isCollection, *recursive, *status) {
	if(*recursive) {
		writeLine("stdout", "implement with tree walk");
	} else {
		if(*isCollection) {
			foreach(*row in SELECT META_COLL_ATTR_VALUE
				WHERE META_COLL_ATTR_NAME = '*key'
				AND COLL_NAME = '*object'
			) {
				msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
				msiString2KeyValPair("*key=*value", *kvPair);
				*status = errorcode(
					msiRemoveKeyValuePairsFromObj(*kvPair, *object, "-C")
				);
			}
		} else {
			foreach(*row in SELECT META_DATA_ATTR_VALUE
				WHERE META_DATA_ATTR_NAME = '*key'
				AND DATA_NAME = '*object'
			) {
				msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
				msiString2KeyValPair("*key=*value", *kvPair);
				*status = errorcode(
					msiRemoveKeyValuePairsFromObj(*kvPair, *object, "-d")
				);
			}
		}
	}
}

# \brief getValueForKey  	If the key exists for the given object, the
# 							value is returned
#
# \param[in] key 			Key to be looked for
# \param[in] object 		Object to look for the key on
# \param[in] isCollection 	Bool indicating wether target object is collection
# \param[out] value 		The first value for the key on that object, if one
# 							exists
uuIiGetValueForKey(*key, *object, *isCollection, *value) {
	*value = "";
	if(*isCollection) {
		foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE COLL_NAME = '*object' 
			AND META_COLL_ATTR_NAME = '*key'
		) {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			break;
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE
			WHERE DATA_NAME = '*object'
			AND META_DATA_ATTR_NAME = '*key'
		) {
			msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
			break;
		}
	}
}

# \brief getValuesForKey  	If the key exists for the given object, all
# 							values are returned
#
# \param[in] key 			Key to be looked for
# \param[in] object 		Object to look for the key on
# \param[in] type 			The object type (d or C)
# \param[out] value 		The values for the key on that object, if at
# 							least one exists, seperated by colons (':')
uuIiGetValuesForKey(*key, *object, *type, *values) {
	*values = "";
	if(*isCollection) {
		foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE COLL_NAME = '*object' 
			AND META_COLL_ATTR_NAME = '*key'
		) {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			if(*values == "") {
				*values = *value;
			} else {
				*values = "*values:*value";
			}
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE
			WHERE DATA_NAME = '*object'
			AND META_DATA_ATTR_NAME = '*key'
		) {
			msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
			if(*values == "") {
				*values = *value;
			} else {
				*values = "*values:*value";
			}
		}
	}
}

# \brief getAllAvailableValuesForKey
# 			Returns a string of all values that exist for a key in the ICAT
#			database. Items are seperated with "#;#"
#
# \param[in] key 			The key to search on
# \param[in] isCollection	Boolean indicating wether the values should be search on
# 							collection metadata (if true) or on data object metadata
# \param[out] values 		String containing all possible values for the key, 
# 							separated by "#;#"
#
uuIiGetAllAvailableValuesForKey(*key, *isCollection, *values) {
	*values = "";
	
	if(*isCollection) {
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = '*key') {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			*values = "*values#;#*value";
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE META_DATA_ATTR_NAME = '*key') {
			msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
			*values = "*values"
		}
	}
}

# \brief getAllAvailableValuesForKey
# 			Returns a string of all values that exist for a key in the ICAT
#			database that match the given search string.
#			Items are seperated with "#;#"
#
# \param[in] key 			The key to search on
# \param[in] isCollection	Boolean indicating wether the values should be search on
# 							collection metadata (if true) or on data object metadata
# \param[in] searchString 	The string to be searched on (LIKE keyword is used, search
# 							string is enclosed in percentage signs)
# \param[out] values 		String containing all possible values for the key, 
# 							separated by "#;#"
#
uuIiGetAvailableValuesForKeyLike(*key, *searchString, *isCollection, *values) {
	*values = "";
	
	if(*isCollection) {
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = '*key' AND META_COLL_ATTR_VALUE like "%*searchString%") {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			*values = "*values#;#*value";
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE META_DATA_ATTR_NAME = '*key' AND META_COLL_ATTR_VALUE like "%*searchString%") {
			msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
			*values = "*values"
		}
	}
}
