# \file
# \brief Contains rules for extracting information from or adding information
#                       to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief getSnapshotHistory     Gets a history of all snapshots created
#                                                               for the current dataset
# \param[in] collection                 Collection name (full path)
# \param[out] buffer                    String of values split by commas, where
#                                                               each value is of format <unix>:userName#userZone
#
uuIiGetSnapshotHistory(*collection, *buffer) {
        *buffer = "";
        foreach(*row in SELECT META_COLL_ATTR_VALUE
                        WHERE META_COLL_ATTR_NAME = 'dataset_snapshot_createdAtBy'
                        AND COLL_NAME = '*collection') {
                msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
                if(strlen(*buffer) == 0) {
                        *buffer = *value;
                } else {
                        *buffer = "*buffer,*value";
                }
        }
}

# \brief getSnapshotHistory     Gets a history of all snapshots created
#                                                               for the current dataset
# \param[in] collection                 Collection name (full path)
# \param[out] time                              Unix timestamp of latest snapshot
# \param[out] userName                  Username of user who created latest snapshot
# \param[out] userZone                  Zone of user who created latest snapshot
#
uuIiGetLatestSnapshotInfo(*collection, *time, *userName, *userZone) {
        *buffer = "";
        *time = 0;
        foreach(*row in SELECT META_COLL_ATTR_VALUE
                        WHERE META_COLL_ATTR_NAME = 'dataset_snapshot_createdAtBy'
                        AND COLL_NAME = '*collection') {
                msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
                *timeAndUser = split(*value, ":");
                *t = int(elem(*timeAndUser, 0));
                if(*t > *time) {
                        *buffer = *value;
                        *time = *t;
                }
        }
        *timeAndUser = split(*buffer, ":");
        if(size(*timeAndUser) > 0) {
                uuGetUserAndZone(elem(*timeAndUser, 1),*userName,*userZone);
        } else {
                *time = 0;
                *userName = "";
                *userZone = "";
        }
}
