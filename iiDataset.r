# \file
# \brief Contains rules for extracting information from or adding information
# 			to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief getSnapshotHistory 	Gets a history of all snapshots created
# 								for the current dataset
# \param[in] collection 		Collection name (full path)
# \param[out] buffer 			All usernames and times
#
uuIiGetSnapshotHistory(*collection) {
	*buffer = list();
	foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE META_COLL_ATTR_NAME = 'dataset_snapshot_createdAtBy'
			AND COLL_NAME = '*collection') {
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
		*datetimeAndUser = split(*value, ":");
		*datetime = elem(*datetimeAndUser, 0);
		*user = uuGetUserAndZone(elem(*datetimeAndUser, 0), *userName, *userZone);
		*elem = (*datetime, *userName, *userZone);
		cons(*elem, *buffer);
	}
}