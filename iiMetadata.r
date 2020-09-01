# \file      iiMetadata.r
# \brief     This file contains rules related to metadata to a dataset.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Remove the User AVU's from the irods AVU store.
#
# \param[in] coll	    Collection to scrub of user metadata
# \param[in] prefix	    prefix of metadata to remov
#
iiRemoveAVUs(*coll, *prefix) {
	#DEBUG writeLine("serverLog", "iiRemoveAVUs: Remove all AVU's from *coll prefixed with *prefix");
	msiString2KeyValPair("", *kvp);
	*prefix = *prefix ++ "%";

	*duplicates = list();
	*prev = "";
	foreach(*row in SELECT order_asc(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		if (*attr == *prev) {
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Duplicate attribute " ++ *attr);
		       *duplicates = cons((*attr, *val), *duplicates);
		} else {
			msiAddKeyVal(*kvp, *attr, *val);
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
			*prev = *attr;
		}
	}

	msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");

	foreach(*pair in *duplicates) {

		(*attr, *val) = *pair;
		#DEBUG writeLine("serverLog", "iiRemoveUserAVUs: Duplicate key Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *attr, *val);
		msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	}
}

# \brief Perform a vault ingest as rodsadmin.
#
iiAdminVaultIngest() {
	msiExecCmd("admin-vaultingest.sh", uuClientFullName, "", "", 0, *out);
}

# \brief iiGetLatestVaultMetadataXml
#
# \param[in] vaultPackage
# \param[out] metadataXmlPath
#
iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath, *metadataXmlSize) {
	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*dataNameQuery = "%*baseName[%].*extension";
	*dataName = "";
	*metadataXmlPath = "";
	foreach (*row in SELECT DATA_NAME, DATA_SIZE WHERE COLL_NAME = *vaultPackage AND DATA_NAME like *dataNameQuery) {
		if (*dataName == "" || (*dataName < *row.DATA_NAME && strlen(*dataName) <= strlen(*row.DATA_NAME))) {
			*dataName = *row.DATA_NAME;
			*metadataXmlPath = *vaultPackage ++ "/" ++ *dataName;
			*metadataXmlSize = int(*row.DATA_SIZE);
		}
	}
}
