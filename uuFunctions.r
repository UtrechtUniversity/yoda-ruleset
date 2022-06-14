# \file uuFunctions.r
# \brief contains functions used to define queries and return timestamps in iso8601 form
#        within iRODS functions are defined differently from rules. A function should have
#        no side effects and should always return a value instead of mutating an output parameter
# \author    Paul Frederiks
# \copyright Copyright (c) 2015-2022, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \function uuiso8601  Return irods style timestamp in iso8601 format
# \param[in] *timestamp		irods style timestamp (epoch as string)
# \returnvalue uuiso8601	string with timestamp in iso8601 format
#
uuiso8601(*timestamp) = timestrf(datetime(int(*timestamp)), "%Y%m%dT%H%M%S%z")


# \brief Checks if a collection exists.
#        Used to be iicollectionexists from Jan de Mooij.
#
# \param[in] collectionname	name of the collection
# \returnvalue boolean, true if collection exists, false if not
#
uuCollectionExists(*collectionname) {
	*exists = false;
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*collectionname') {
		*exists = true;
		break;
	}
	*exists;
}

# \brief Check if a file exists in the catalog.
#
# \param[in] *path
# \returnvalue  boolean, true if collection exists, false if not
#
uuFileExists(*path) {
	*exists = false;
	uuChopPath(*path, *collName, *dataName);
	foreach (*row in SELECT DATA_ID WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
		*exists = true;
		break;
	}
	*exists;
}

# \brief Return a key-value-pair of metadata associated with a dataobject.
#	 If a key is defined multiple times, the last found will be returned.
#
# \param[in]  data_id	Unique DataObject ID. Used because it is Unique
# \param[in]  prefix	Only include metadata with this prefix
# \param[in,out] kvp	key-value-pair to add the metadata to
#
uuObjectMetadataKvp(*data_id, *prefix, *kvp) {
	*ContInxOld = 1;
	msiMakeGenQuery("META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE", "DATA_ID = '*data_id'", *GenQInp);
	if (*prefix != "") {
		#| writeLine("stdout", "prefix is *prefix");
		msiAddConditionToGenQuery("META_DATA_ATTR_NAME", " like ", "*prefix%%", *GenQInp);
	}
	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
	while(*ContInxOld > 0) {
		foreach(*meta in *GenQOut) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			msiAddKeyVal(*kvp, *name, *val);
		}
		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQInp, *GenQOut);
}
