# \file      iiBrowse.r
# \brief     Rules to support the research area browser
# \author    Lazlo Westerhof
# \author    Paul Frederiks
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# \brief iiListLocks
iiListLocks(*path, *offset, *limit, *result, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "";
	iiGetLocks(*path, *locks);
	*total = size(*locks);
	for(*i = 0; *i < *offset;*i = *i + 1) {
		if (size(*locks) == 0) {
			break;
		}
		*locks = tl(*locks);
	}
	*nLocks = size(*locks);
	if (*nLocks == 0) {
		*status = "NoLocksFound";
		*statusInfo = "No Locks Found";
		*more = 0;
		*returned = 0;
		*json_arr = "[]";
	} else if (*nLocks > *limit) {
		*status = "Success";
		*more = *nLocks - *limit;
		*returnedLocks = list();
		for(*i = 0; *i < *limit; *i = *i + 1) {
			*lock = elem(*locks, *i);
			*returnedLocks = cons(*lock, *returnedLocks);
		}
		*returned = *limit;
		uuList2JSON(*returnedLocks, *json_arr);
	} else {
		*status = "Success";
		*returned = size(*locks);
		*more = 0;
		uuList2JSON(*locks, *json_arr);
	}
	*kvp.locks = *json_arr;
	*kvp.total = str(*total);
	*kvp.more = str(*more);
	*kvp.returned = str(*returned);
	uuKvp2JSON(*kvp, *result);
}

# \brief iiCollectionMetadataKvpList
# \param[in] path

iiCollectionMetadataKvpList(*path, *prefix, *strip, *lst) {
	*lst = list();
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *path
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		if (*strip) {
			*kvp.attrName = triml(*row.META_COLL_ATTR_NAME, *prefix);
		} else {
			*kvp.attrName = *row.META_COLL_ATTR_NAME;
		}
		*kvp.attrValue = *row.META_COLL_ATTR_VALUE;
		*lst = cons(*kvp, *lst);
	}
}

# \brief iiDataObjectKvpList
iiDataObjectMetadataKvpList(*path, *prefix, *strip, *lst) {
	*lst = list();
	uuChopPath(*path, *collName, *dataName);
	foreach(*row in SELECT META_DATA_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *collName
		AND DATA_NAME = *dataName
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		if (*strip) {
			*kvp.attrName = triml(*row.META_DATA_ATTR_NAME, *prefix);
		} else {
			*kvp.attrName = *row.META_DATA_ATTR_NAME;
		}
		*kvp.attrValue = *row.META_DATA_ATTR_VALUE;
		*lst = cons(*kvp, *lst);
	}
}
