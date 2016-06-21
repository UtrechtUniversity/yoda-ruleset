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

# \brief getFilteredMembers     Returns a list of members of a group, filtered by role
#
# \param[in] groupName          Name of the group
# \param[in] showAdmins         Boolean, indicating wether to include group administrators
# \param[in] showUsers          Boolean, indicating wether to include users w/ read/write access
# \param[in] showReadonly       Boolean, indicating wether to include users w/ readonly access
# \param[out] memberList        List of group members, filtered by means of argument values
#
uuIiGetFilteredMembers(*groupName, *showAdmins, *showUsers, *showReadonly, *memberList) {
        uuGroupGetMembers(*groupName, *members);
        *buffer = "";
        foreach(*userName in *members) {
                uuGroupUserIsManager(*groupName, *userName, *isManager)
                if(*showAdmins && *isManager || *showUsers && !*isManager) {
                        *buffer = "*buffer;*userName";
                }
        }
        *memberList = split(*buffer, ";");
}