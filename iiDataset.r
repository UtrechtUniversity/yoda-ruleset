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
# uuIiGetSnapshotHistory(*collection, *buffer) {
# 	*buffer = list();
# 	foreach(*row in SELECT order_asc(META_COLL_ATTR_VALUE)
# 		WHERE META_COLL_ATTR_NAME = 'dataset_snapshot_createdAtBy'
# 		AND COLL_NAME = '*collection') {
# 		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
# 		*segments = split(*value, ":");
# 		*datasetID = elem(*segments, 1);
# 		if(size(*segments) > 2) { #legacy bug
# 			foreach(*row in SELECT COLL_NAME WHERE COLL_ID = '*datasetID') {
# 				*name = *row.COLL_NAME;
# 				*value = "*name#*value";
# 				break;
# 			}
# 		} else {
# 				*value = "#::*value";
# 			}
# 		*buffer = cons(*value, *buffer);
# 	}
# }

uuIiGetIntakeRootFromIntakePath(*path, *intakeRoot) {
	uuIiGetIntakePrefix(*intakePrefix);
    uuChop(*path, *head, *tail, *intakePrefix, true);
    uuChop(*tail, *groupName, *leftover, "/", true);
    *intakeRoot = *head ++ substr(*intakePrefix, strlen(*intakePrefix) - 1, strlen(*intakePrefix)) ++ *groupName;
}

uuIiGetSnapshotHistory(*collection, *buffer) {
	uuIiGetIntakeRootFromIntakePath(*collection, *intakeRoot);
	uuIiGetVaultrootFromIntake(*intakeRoot, *vaultRoot);
	uuIiSnapshotGetVaultParent(*vaultRoot, *collection, *vaultParent);

	*buffer = list();
	foreach(*row in SELECT order_asc(META_COLL_ATTR_VALUE), META_COLL_ATTR_NAME, COLL_NAME WHERE
		COLL_PARENT_NAME = '*vaultParent' 
	) {
		if(*row.META_COLL_ATTR_NAME == 'snapshot_version_information') {
			*coll = *row.COLL_NAME;
			*info = *row.META_COLL_ATTR_VALUE;
			*buffer = cons("*coll#*info", *buffer);
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
uuIiGetLatestSnapshotInfo(*collection, *version, *datasetID, *datasetPath, *time, *userName, *userZone) {
	*buffer = "";
	*time = 0;
	
	uuIiGetIntakeRootFromIntakePath(*collection, *intakeRoot);
	uuIiGetVaultrootFromIntake(*intakeRoot, *vaultRoot);
	uuIiSnapshotGetVaultParent(*vaultRoot, *collection, *vaultParent);

	foreach(*row in SELECT order_desc(META_COLL_ATTR_VALUE) WHERE 
		META_COLL_ATTR_NAME = 'snapshot_version_information'
		AND COLL_PARENT_NAME = '*vaultParent'
	) {
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *log);
		*values = split(*log, "#");

		writeLine("serverLog", "Found values *log, which splits into *values");

		*version = elem(*values, 0);
		*datasetID = elem(*values, 4);
		*datasetPath = elem(*values, 5);
		*time = elem(*values, 1);
		*userName = elem(*values, 2);
		*userZone = elem(*values, 3);
		break;
	}
}

uuIiGetVersionAndBasedOn(*collection, *version, *basedOn) {
	*version = "";
	*basedOn = "";
	uuIiVersionKey(*versionKey, *dependsKey)
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = '*collection'
	) {
		if(*row.META_COLL_ATTR_NAME == '*versionKey') {
			*version = *row.META_COLL_ATTR_VALUE;
		} else if(*row.META_COLL_ATTR_NAME == '*dependsKey') {
			*dId = *row.META_COLL_ATTR_VALUE;
			foreach(*newRow in SELECT COLL_NAME WHERE COLL_ID = '*dId') {
				*basedOn = *newRow.COLL_NAME;
				break;
			}
		}
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

# \brief getDirectories         Returns all collections that match the criteria. Requires
#                               read access on the project the directories are in
# 
# \param[in] showProjects       Show collections that serve as project root
# \param[in] showStudies        Show collections that serve as study root
# \param[in] showDatasets       Show collections that serve as datapackage root
# \param[in] showSubcollections Show collections that appear inside a data package
# \param[in] requiresContribute Show directories the user has at least contribute access to
# \param[in] requiresManager    Show directories the user has at least manager access to
# \param[out] directoryList     List of directories that match the criteria
#
uuIiGetDirectories(
	*showProjects, 
	*showStudies, 
	*showDatasets, 
	*requiresContribute, 
	*requiresManager,
	*directoryList ) {

	*directories = "";
	if((*showProjects || *showStudies || *showDatasets)) {
		*user = "$userNameClient#$rodsZoneClient";
		uuGroupMemberships(*user, *groups);
		uuIiGetIntakePrefix(*intakePrefix);
		foreach(*group in *groups) {
			uuGroupUserIsManager(*group, *user, *isManager);
			if(!*requiresManager || *isManager){
				#TODO: adapt for readonly role addition
				writeLine("stdout", *group);
				writeLine("stdout", *intakePrefix);
				writeLine("stdout", *group like '*intakePrefix*');
				writeLine("stdout", "\n");
				if(*group like "*intakePrefix*") {
					foreach(*project in SELECT COLL_NAME WHERE COLL_NAME like '%/*group') {
						*cn = *project.COLL_NAME;
						if(*cn like "/$rodsZoneClient/home/*") {
							if(*showProjects){
								*directories = "*directories:*cn";
							}
							if(*showStudies || *showDatasets) {
								foreach(*study in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '*cn') {
									*sn = *study.COLL_NAME;
									if(*showStudies) {
										*directories = "*directories:*sn";
									}
									if(*showDatasets) {
										foreach(*dataset in SELECT COLL_NAME WHERE COLL_PARENT_NAME = '*sn') {
											*dn = *dataset.COLL_NAME;
											if(*showDatasets) {
												*directories = "*directories:*dn";
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}
		*directories = triml(*directories,":");
		*directoryList = split(*directories, ":");
	} else {
		*directoryList = list();
	}
}
