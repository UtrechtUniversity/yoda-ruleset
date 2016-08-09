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

# \brief uuIiGetValuesForKeys 	Extracts the values (multiple if available) for a
# 								list of keys in string format separated by a custom
# 								other string.
#
# \param[in] object 			Object to get meta data from
# \param[in] keys 				List of keys to get values for, seperated with *keySepChar
# \param[in] keySepChar 		String that is used as separator between keys in *keys and
# 								between key-value pairs in *result
# \param[in] valueSepChar 		String that is used as separator in between values for a
# 								certain key.
# \param[out] result 			String that contains key-value pairs for all values for
# 								all keys from *keys, where the key-value pairs are 
# 								separated from each other with *keySepChar and the values
# 								for a single key are separated with *valueSepChar
#
uuIiGetValuesForKeys(*object, *keys, *keySepChar, *valueSepChar, *result) {
	msiGetObjType(*object, *type);

	*tail = *keys;
	*currentKey = "";
	*currentValues = "";
	*result = "";

	uuExplode(*keys, *keySepChar, *keyList);

	foreach(*item in *keyList){
		if(*type == "-d") {
			*query = SELECT META_DATA_ATTR_VALUE WHERE DATA_NAME = '*object' AND META_DATA_ATTR_NAME = '*item';
		} else if(*type == "-c") {
			*query = SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '*object' AND META_COLL_ATTR_NAME = '*item';
		} else {
			*result = "Object must be collection or data object";
			return;
		}

		foreach(*row in *query) {
			if(*type == "-d") {
				msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
			} else {
				msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			}
			if(*currentKey == *item) {
				*currentValues = "*currentValues*valueSepChar*value";
			} else {
				*result = "*result*keySepChar*currentKey*valueSepChar*currentValues";
				*currentKey = *item;
				*currentValues = *value;
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

# \brief uuExplode 	Explode a string based on a random seprator string
#
# \param[in] string 		String that contains items
# \param[in] separator		separator char or string (any length)
# \param[out] resultList 	List of items that appear in string separated
# 							by *separator
#
uuExplode(*string, *separator, *resultList) {
	*tail = *string;
	*result = list();
	while(strlen(*tail) > strlen(*separator)) {
		*newTail = trimr(*tail, *separator);
		*head = substr(*tail, strlen(*newTail) + strlen(*separator), strlen(*tail));
		*result = cons(*head, *result);
		*tail = *newTail;
	}

	*resultList = cons(*tail, *result);
}

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
			META_COLL_ATTR_NAME = '*key' AND
			META_COLL_ATTR_VALUE like '%*searchString%') {
			writeLine("stdout", *row.META_COLL_ATTR_VALUE);
			*values = cons(*row.META_COLL_ATTR_VALUE,*values);
			writeLine("serverLog", *row.META_COLL_ATTR_VALUE);
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE 
			META_DATA_ATTR_NAME = '*key' AND
			META_DATA_ATTR_VALUE like '%*searchString%') {
			*values = cons(*row.META_DATA_ATTR_VALUE,*values);
		}
	}
}

