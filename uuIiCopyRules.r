
# \file
# \brief move all datasets that have a to_vault_lock metatag from intake area to the vault area
#        this rule is to be executed by a background process with write access to vault
#			and read access to the intake area.
#			This file is based on yc2Vault.r
#
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE

# \brief move all locked datasets to the vault
#
# \param[in]  intakeCollection  pathname root of intake area (/{zone}/{home}/grp-intake-{goup})
# \param[in]  vaultCollection   pathname root of vault area (/{zone}/{home}/grp-intake-{goup})
# \param[out] status            result of operation either "ok" (0) or "error" (non-zero)
#
uuIi2Vault(*intakeRoot, *vaultRoot, *status) {
	# 1. add to_vault_freeze metadata lock to the dataset
	# 2. check that dataset does not yet exist in the vault
	# 3. copy dataset to vault with its metadata
	# upon any error:
	# - delete partial data from vault
	# - add error to intake dataset metadata
	# - remove locks on intake dataset (to_vault_freeze, to_vault_lock)
	*status = 0; # 0 is success, nonzero is error

	foreach (*row in SELECT COLL_NAME, META_COLL_ATTR_VALUE
				WHERE META_COLL_ATTR_NAME = 'dataset_snapshotlock_toplevel'
				  AND COLL_NAME like '*intakeRoot/%') {
		msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);

		uuChopPath(*topLevelCollection, *parent, *datasetId);
		iiObjectIsSnapshotLocked(*topLevelCollection, true, *locked, *frozen);

		if (*locked) {
			uuLock(*topLevelCollection, *lockStatus);
			*lockStatus = 0;
			if(*lockStatus == 0) {
				iiDatasetSnapshotFreeze(*topLevelCollection, *status);
				
				# datset frozen, now move to fault and remove from intake area
				uuIiDatasetCollectionCopy2Vault(
						*intakeRoot, 
						*topLevelCollection,
						*datasetId,
						*vaultRoot,
						*status
					);

				if(*status == 0) {
					uuIiAddSnapshotLogToCollection(*topLevelCollection, *status);
					iiDatasetSnapshotMelt(*topLevelCollection, *status);
					iiDatasetSnapshotUnlock(*topLevelCollection, *status);
				}
			}
		}
		uuUnlock(*topLevelCollection);
	}
}

# \brief uuIiAddSnapshotLogToCollection Adds the metadata value from 
#										'dataset_snapshotlock_toplevel'
# 										to the dataset toplevel as 
# 										'dataset_snapshot_createdAtBy' so
# 										a complete history of snapshots can
# 										be extracted from the metadata later
# \param[in] collection 				Dataset parent collection
# \param[in] datasetId 					Dataset name
uuIiAddSnapshotLogToCollection(*collection, *status) {
	writeLine("serverLog", "Finding metadata for '*collection'");
	foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE META_COLL_ATTR_NAME = 'dataset_snapshotlock_toplevel'
			AND COLL_NAME = "*collection"
		) {
			writeLine("serverLog", "Found *row");
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			msiString2KeyValPair("dataset_snapshot_createdAtBy=*value", *kvPair);
			*status = errorcode(
					msiAssociateKeyValuePairsToObj(*kvPair, "*collection", "-C")
				);
			writeLine("serverLog", "Finished updating createdAtBy (*value) with status *status");
		}
}

# \brief uuIiDatasetCollectionCopy2Vault Copies a dataset recursively to the vault
# 
# \param[in] intakeRoot 			The path to the root of the intake group of the dataset
#										that is to be copied to the vault,
#										e.g. /{zone}/{home}/grp-intake-{goup}
# \param[in] topLevelCollection		The full path to the dataset. *intakeRoot/*datasetId
# \param[in] datasetId				The base name of the dataset that is to be copied to
#										the vault
# \param[in] vaultRoot 				The full path to the root of the vault for a group,
#										e.g. /{zone}/{home}/grp-vault-{goup}
# \param[out] status 				Integer exitcode, non-zero means fail (see logs)
#
uuIiDatasetCollectionCopy2Vault(*intakeRoot, *topLevelCollection, *datasetId, *vaultRoot, *status) {
	*status = 0;
	iiGetOwner(*topLevelCollection, *owner);
	iiCollectionExists(*vaultRoot, *vaultRootExists);
	if(*vaultRootExists) {
		# uuIiVaultSnapshotGetPath(*vaultRoot, *datasetId, *owner, *vaultPath)
		uuIiVaultSnapshotGetSecondPath(*vaultRoot, *topLevelCollection, *vaultPath);
		iiCollectionExists(*vaultPath, *exists);
		if (!*exists) {
			# create the in-between levels of the path to the toplevel collection
			uuChopPath(*vaultPath, *vaultParent, *vaultCollection);
			*status = errorcode(msiCollCreate(*vaultParent, "1", *status));	
			if (*status >= 0) {
				# copy the dataset tree to the vault
				uuChopPath(*topLevelCollection, *intakeParent, *intakeCollection);
				*buffer."source" = *topLevelCollection;
				*buffer."destination" = *vaultPath;
				uuTreeWalk(
						"forward", 
						*topLevelCollection,
						"uuIiVaultWalkIngestObject",
						*buffer,
						*status
					);
				uuKvClear(*buffer);
				if (*status == 0) {
					# stamp the vault dataset collection with additional metadata
					uuIiCopyParentsMetadata(*topLevelCollection, *vaultPath, *parentMetaStatus);
					uuIiUpdateVersion(*topLevelCollection, *vaultPath, *versionBumbStatus);
					msiGetIcatTime(*date, "unix");
					msiAddKeyVal(*kv, "snapshot_date_created", *date);
					msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
					uuChopPath(*vaultPath, *vaultDatasetRoot, *vaultBase)
					iiDatasetSnapshotMelt(*vaultPath, *status);
					iiDatasetSnapshotUnlock(*vaultPath, *status);
					uuUnlock(*vaultPath);
				} else {
					# move failed (partially), cleanup vault
					# NB: keep the dataset in the vault queue so we can retry some other time
					writeLine("serverLog","ERROR: Ingest failed for *datasetId error = *status");

					# TODO
					uuTreeWalk("reverse", *vaultPath, "uuYcVaultWalkRemoveObject", *buffer, *error);
				}
			}
		} else {
			writeLine("serverLog","INFO: version already exists in vault: *datasetId");
			# duplicate dataset, signal error and throw out of vault queue
			*message = "Duplicate dataset, version already exists in vault";
			uuYcDatasetErrorAdd(*intakeRoot, *datasetId,*message);
			iiDatasetSnapshotMelt(*topLevelCollection, *status);
			iiDatasetSnapshotUnlock(*topLevelCollection, *status);

			# uuYcDatasetMelt(*topLevelCollection, *datasetId, *status);
			# uuYcDatasetUnlock(*topLevelCollection, *datasetId, *status);
			*status = 1; # duplicate dataset version error
		}
	} else {
		writeLine("serverLog", "INFO: Vault root *vaultRoot does not exist. Snapshot failed");
		*message = "Vault root *vaultRoot does not exist.";
		uuYcDatasetErrorAdd(*intakeRoot, *datasetId,*message);
		iiDatasetSnapshotMelt(*topLevelCollection, *status);
		iiDatasetSnapshotUnlock(*topLevelCollection, *status);
		*status = 1; # duplicate dataset version error
	}
}

# \brief uuIiCopyParentsMetadata 	Crawls over all parents of a collection and
# 									adds the meta data of all those collections
# 									from which they keys start with the metadata
# 									prefix to vault version of the collection
#
# \param[in] topLevelCollection 	The collecting which has parents from which
# 									the metadata should be extracted
# \param[in] vaultPath 				The path to the collection to which the 
# 									metadata should be added
# \param[out] Status 				Error code. 0 indicating success, -100 indicating
# 									the logs should be checked
#
uuIiCopyParentsMetadata(*topLevelCollection, *vaultPath, *status) {
	*status = 0;
	uuChopPath(*topLevelCollection, *parent, *base);
	*pathStart = "/"++$rodsZoneClient++"/home/";
	uuIiGetMetadataPrefix(*prfx);
	while(*parent like "*pathStart\*" && *parent != *pathStart) {
		foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
			WHERE COLL_NAME = "*parent" AND 
			META_COLL_ATTR_NAME like "*prfx%"
		) {
			*key = "";
			*value = "";
			*s1 = errorcode(msiGetValByKey(*row, "META_COLL_ATTR_NAME", *key));
			*s2 = errorcode(msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value));
			*s3 = errorcode(msiString2KeyValPair("*key=*value",*kv));
			*s4 = errorcode(msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C"));
			if(*s1 != 0 || *s2 != 0 || *s3 != 0 || *s4 != 0) {
				*msg = "WARNING: Something went wrong in extracing or updating the medatadata";
				*msg = "*msg from '*parent'. The extracted key was '*key' and the extracted value was '*value'";
				writeLine("serverLog", *msg);
				*status = -100;
			}
		}
		uuChopPath(*parent, *parent_new, *base);
		*parent = *parent_new;
	}
}

# \brief uuIiUpdateVersion 	Increments the version number of the collection
# 							by one, and sets the depends metadata value to
#							the unique ID of the dataset belonging to the
# 							vaultPath
#
# \param[in] topLevelCollection 	Collection name of the top level collection
# \param[in] vaultPath 				Collection name of the vault collection, 
# 									from which the collection ID is used
# \param[out] status 				The error code of updating the metadata
#
uuIiUpdateVersion(*topLevelCollection, *vaultPath, *status) {
	uuIiVersionKey(*versionKey, *dependsKey);
	*version = 0;
	*depends = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE 
		COLL_NAME = "*topLevelCollection" AND 
		META_COLL_ATTR_NAME = "*versionKey"
	) {
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
		writeLine("stdout", "Found version *value");
		*version = int(*value) + 1;
		writeLine("stdout", "New version is *version");
		break;
	}

	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = "*vaultPath") {
		msiGetValByKey(*row, "COLL_ID", *depends);
		break;
	}

	writeLine("stdout", "Going to set version to *version, and depends to *depends");

	msiAddKeyVal(*kv, *versionKey, str(*version));
	msiAddKeyVal(*kv, *dependsKey, *depends);
    *status = errorcode(msiSetKeyValuePairsToObj(*kv, *topLevelCollection, "-C"));
    writeLine("stdout", "Finished updating version with status *status");
}

# \brief uuIiVaultWalkIngestObject 	Treewalkrule, that calculates the objectPath and
# 									vaultPath for each object it is called on, and calls
#									the uuIiVaultIngestObject function to copy the meta
#									data from the object to the backup in the vault
# \param[in] itemParent 			The COLL_NAME of the direct parent collection of this
# 										object
# \param[in] itemName 				The name of this object
# \param[in] isCollection 			Bool, true iff object is collection
# \param[in\out] buffer				A buffer object containing the top level source of the
#										object as "source"
# \param[out] status 				Integer exit code, non-zero means fail
#										
uuIiVaultWalkIngestObject(*itemParent, *itemName, *itemIsCollection, *buffer, *status) {
	*sourcePath = "*itemParent/*itemName";
	*destPath = *buffer."destination"; # top level destination is specified 
	if (*sourcePath != *buffer."source") {
		# rewrite path to copy objects that are located underneath the toplevel collection
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
	}
	uuIiVaultIngestObject(*sourcePath, *itemIsCollection, *destPath, *status); 
}

# \brief uuIiVaultIngestObject 	Copies metadata from the source dataset
#								to the copy of the dataset in the vault
# \param[in] objectPath 	Path to the object that should be ingested
# \param[in] isCollection 	Bool, true iff the object is a collection
# \param[in] vaultPath 		Path to the copy of the object in the vault
# \param[out] status 		Integer exitcode, non-zero means error
#
uuIiVaultIngestObject(*objectPath, *isCollection, *vaultPath, *status) {
	*status = 0;
	if (*isCollection) {
		msiCollCreate(*vaultPath, "1", *status);
		if (*status == 0) {
			foreach (*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
								WHERE COLL_NAME = '*objectPath'
			) {
				msiGetValByKey(*row, "META_COLL_ATTR_NAME", *key);
				msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
				msiString2KeyValPair("*key=*value",*kv);
				msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
			}
			foreach (*row in SELECT COLL_OWNER_NAME, COLL_OWNER_ZONE, COLL_CREATE_TIME
								WHERE COLL_NAME = '*objectPath'
			) {
				msiGetValByKey(*row, "COLL_OWNER_NAME", *ownerName);
				msiGetValByKey(*row, "COLL_OWNER_ZONE", *ownerZone);
				msiGetValByKey(*row, "COLL_CREATE_TIME", *createTime);
				msiString2KeyValPair("submitted_by=*ownerName#*ownerZone",*kvSubmittedBy);
				msiString2KeyValPair("submitted_date=*createTime",*kvSubmittedDate);
				msiAssociateKeyValuePairsToObj(*kvSubmittedBy, *vaultPath, "-C");
				msiAssociateKeyValuePairsToObj(*kvSubmittedDate, *vaultPath, "-C");
			}
		}
	} else {   # its not a collection but a data object
		# first chksum the orginal file then use it to verify the vault copy
		msiDataObjChksum(*objectPath, "forceChksum=", *checksum);
		*status = errorcode(msiDataObjCopy(*objectPath, *vaultPath, "verifyChksum=", *status));
		if (*status == 0) {
			uuChopPath(*objectPath, *collection, *dataName);
			foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
								      WHERE COLL_NAME = '*collection'
								        AND DATA_NAME = '*dataName'
			) {
				msiGetValByKey(*row, "META_DATA_ATTR_NAME", *key);
				msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
				msiString2KeyValPair("*key=*value",*kv);
				msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-d");
			}
			# add metadata found in system info
			foreach (*row in SELECT DATA_OWNER_NAME, DATA_OWNER_ZONE, DATA_CREATE_TIME
				                  WHERE COLL_NAME = '*collection'
				                    AND DATA_NAME = '*dataName'
			) {
				msiGetValByKey(*row, "DATA_OWNER_NAME", *ownerName);
				msiGetValByKey(*row, "DATA_OWNER_ZONE", *ownerZone);
				msiGetValByKey(*row, "DATA_CREATE_TIME", *createTime);
				msiString2KeyValPair("submitted_by=*ownerName#*ownerZone",*kvSubmittedBy);
				msiString2KeyValPair("submitted_date=*createTime",*kvSubmittedDate);
				msiAssociateKeyValuePairsToObj(*kvSubmittedBy, *vaultPath, "-d");
				msiAssociateKeyValuePairsToObj(*kvSubmittedDate, *vaultPath, "-d");
			}
		}
	}
}


# \brief get the path of the study in the vault, which is always of the from
# 	{zone}/home/grp-vault-{studyID}/{ownername}/{datasetname}/{unixtime}
#
# \param[in]	vaultRoot 	The root path of the vault (zone + grp-vault-<study>)
# \param[in]	datasetId	The name of the dataset itself (the name of the directory
#							inside the intake study)
# \param[in] 	owner 		Name of owner of dataset
# \param[out]	vaultPath 	The full path to the vault for this dataset and version
uuIiVaultSnapshotGetPath(*vaultRoot, *datasetId, *owner, *vaultPath) {
	msiGetIcatTime(*time, "unix");
   	*vaultPath = str("*vaultRoot/*owner/*datasetId/*time");
}

uuIiVaultSnapshotGetSecondPath(*vaultRoot, *topLevelCollection, *vaultPath) {
	msiGetIcatTime(*time, "human");
	*pathStart = "/$rodsZoneClient/home";
	*segmentsWithRoot = substr(*topLevelCollection, strlen(*pathStart), strlen(*topLevelCollection));
	uuChop(*segmentsWithRoot, *group, *segments, "/", true);

	*vaultPath = "*vaultRoot/*segments/*time";
}

# \brief iiCollectionExists Checks if a collection exists
#
# \param[in] collectionName	Name of the collection
# \parmam[out] exists 		Bool, true iff exists
iiCollectionExists(*collectionName, *exists) {
	*exists = false;
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*collectionName') {
		*exists = true;
		break;
	}
}

iiGetOwner(*path, *owner) {
	foreach(*row in SELECT COLL_OWNER_NAME WHERE COLL_NAME = "*path") {
		*owner = *row.COLL_OWNER_NAME;
	}

	foreach(*row in SELECT META_COLL_ATTR_VALUE 
		WHERE COLL_NAME = "*path" 
		AND META_COLL_ATTR_NAME = "dataset_owner") {
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *owner);
	}
}