# \file
# \brief     UU - Metadata functions.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.txt.

# \brief Sets metadata on an object.
#
# \param[in] path
# \param[in] key
# \param[in] value
# \param[in] type  either "-d" for data objects or "-C" for collections
#
# \todo Add an "overwrite" parameter.
#
uuSetMetaData(*path, *key, *value, *type) {
	msiAddKeyVal(*kv, *key, *value);
	#errorcode(msiAddKeyVal(*kv, *key, *value));
	#*kv.*key = *value;
	msiAssociateKeyValuePairsToObj(*kv, *path, *type);
}


# \brief Removes metadata from an object.
#
# \param[in] path
# \param[in] key
# \param[in] value
# \param[in] type  either "-d" for data objects or "-C" for collections
#
# \todo Add a parameter that allows removing all values for a certain key.
#
uuRemoveMetaData(*path, *key, *value, *type) {
	msiAddKeyVal(*kv, *key, *value);
	#errorcode(msiAddKeyVal(*kv, *key, *value));
	#*kv.*key = *value;
	msiRemoveKeyValuePairsFromObj(*kv, *path, *type);
}
