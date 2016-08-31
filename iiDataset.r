# \file
# \brief Contains rules for extracting information from or adding information
#                       to a dataset
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief getIntakeRootFromIntakePath 	Uses the defined intake prefix
# 										to try and find the root of a
#										group
# 
# \param[in] path 						The path to a collection
# \param[out] intakeRoot 				The path to the groups rot
# 
uuIiGetIntakeRootFromIntakePath(*path, *intakeRoot) {
	uuIiGetIntakePrefix(*intakePrefix);
    uuChop(*path, *head, *tail, *intakePrefix, true);
    uuChop(*tail, *groupName, *leftover, "/", true);
    *intakeRoot = *head ++ substr(*intakePrefix, strlen(*intakePrefix) - 1, strlen(*intakePrefix)) ++ *groupName;
}

# \brief getSnapshotHistory 	Queries the vault for a certain collection
# 								for existing versions, and concats some
# 								information about all versions to a string
#
# \param[in] collection 		The path to a collection
# \param[out] buffer 			Strings separated by hashtags that contain
# 								information about existing versions
#
uuIiGetSnapshotHistory(*collection, *buffer) {
	uuIiGetIntakeRootFromIntakePath(*collection, *intakeRoot);
	uuIiGetVaultrootFromIntake(*intakeRoot, *vaultRoot);
	uuIiSnapshotGetVaultParent(*vaultRoot, *collection, *vaultParent);

	*buffer = list();
	foreach(*row in SELECT META_COLL_ATTR_VALUE, META_COLL_ATTR_NAME, order_asc(COLL_NAME) WHERE
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

	*version = "";
	*time = "";
	*userName = "";
	*userZone = "";
	*datasetID = "";
	*datasetPath = "";
	
	uuIiGetIntakeRootFromIntakePath(*collection, *intakeRoot);
	uuIiGetVaultrootFromIntake(*intakeRoot, *vaultRoot);
	uuIiSnapshotGetVaultParent(*vaultRoot, *collection, *vaultParent);

	foreach(*row in SELECT order_desc(COLL_NAME), META_COLL_ATTR_VALUE WHERE 
		META_COLL_ATTR_NAME = 'snapshot_version_information'
		AND COLL_PARENT_NAME = '*vaultParent'
	) {
		*log = "";
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *log);

		writeLine("serverLog", "*log");



		uuChop(*log, 		*version, 		*rest1, 	"#", 	true);
		uuChop(*rest1,		*time, 			*rest2,		"#",	true);
		uuChop(*rest2, 		*userName, 		*rest3, 	"#", 	true);
		uuChop(*rest3, 		*userZone, 		*rest4, 	"#", 	true);
		uuChop(*rest4, 		*datasetID,		*rest5, 	"#", 	true);
		uuChop(*rest5, 		*datasetPath, 	*tail, 		"#", 	true);

		writeLine("serverLog", "Found version=*version, username=*userName, userzone=*userZone, datasetID=*datasetID, datasetPath=*datasetPath");

		break;
	}
}

# \brief GetVersionAndBasedOn 		Queries a collection to see if it has
# 									version information. If so, it extracts
# 									the version and the ID of the collection
# 									this version was based on from the meta data
#
# \param[in] collection 			Path to a collection
# \param[out] version 				Version number of *collection
# \param[out] basedOn 				The collection ID of the collection 
# 									*collection was based on
#
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

# \brief IntakerStudies 	Finds all groups a user is
# 							a member of and which have
# 							the intake prefix
#
# \param[out] 				String containing all group
# 							names the current user has
# 							access to, stripped of the
#							intake prefix and separated
# 							by commas
uuIiIntakerStudies(*studies){
	uuGroupMemberships($userNameClient,*groups);
	*studies="";
	uuIiGetIntakePrefix(*prefix)
	foreach (*group in *groups) {
		if (*group like "*prefix*") {
			*study = triml(*group,*prefix);
			*studies="*studies,*study";
		}
	}
	*studies=triml(*studies,",");
}
