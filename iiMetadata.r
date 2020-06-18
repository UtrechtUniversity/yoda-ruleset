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

# \brief iiLogicalPathFromPhysicalPath
#
# \param[in]  physicalPath
# \param[out] logicalPath
# \param[in]  zone
#
iiLogicalPathFromPhysicalPath(*physicalPath, *logicalPath, *zone) {
	*lst = split(*physicalPath, "/");
	# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
	uuListIndexOf(*lst, "home", *idx);
	if (*idx < 0) {
		writeLine("serverLog","iiLogicalPathFromPhysicalPath: Could not find home in *physicalPath. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		fail;
	}
	# skip to the part of the path starting from ../home/..
	for( *el = 0; *el < *idx; *el = *el + 1) {
		*lst = tl(*lst);
	}
	# Prepend with the zone and rejoin to a logical path
	*lst	= cons(*zone, *lst);
	uuJoin("/", *lst, *logicalPath);
	*logicalPath = "/" ++ *logicalPath;
	#DEBUG writeLine("serverLog", "iiLogicalPathFromPhysicalPath: *physicalPath => *logicalPath");
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
