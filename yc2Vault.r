# \file
# \brief move selected datasets from intake area to the vault area
#        this rule is to be executed by a background process with write access to vault
#			and read access to the intake area
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#test {
#	*intakeRoot = '/nluu1ot/home/grp-intake-youth';
#	*vaultRoot = '/nluu1ot/home/grp-vault-youth';
#	uuYc2Vault(*intakeRoot, *vaultRoot, *status);
#	writeLine("serverLog","result status of yc2Vault is *status");
#}


# \brief
#
# \param[in] path  pathname of the tree-item
# \param[in] name  segment of path, name of collection or data object
# \param[in] isCol  true if the object is a collection, otherwise false
# \param[in,out] buffer
#
#uuTreeMyRule(*parent, *objectName, *isCol, *buffer) {
#	writeLine("serverLog","parent      = *parent");
#	writeLine("serverLog","name        = *objectName");
#	writeLine("serverLog","isCol       = *isCol");
#	writeLine("serverLog","buffer[path]= " ++ *buffer."path");
#	if (*isCol) {
#	   *buffer."path" = *buffer."path"++"=";
#	}
#}




uuYcVaultDatasetGetPath(*vaultRoot, *datasetId, *datasetPath) {
	uuYcDatasetParseId(*datasetId, *datasetComponents);
	*wave = *datasetComponents."wave";
	*experimentType = *datasetComponents."experiment_type";
	*pseudocode = *datasetComponents."pseudocode";
	*version = *datasetComponents."version";
	*sep = "_"; 
	*wepv = *wave ++ *sep ++ *experimentType ++ *sep ++ *pseudocode ++ *sep ++ "ver*version";
   *datasetPath = "*vaultRoot/*wave/*experimentType/*pseudocode/*wepv";
}

uuYcVaultDatasetExists(*vaultRoot, *datasetId, *exists) {
	*exists = false;
	uuYcVaultDatasetGetPath(*vaultRoot, *datasetId, *datasetPath);
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*datasetPath') {
		*exists = true;
		break;
	}
}


uuYcVaultDatasetAddMeta(*vaultPath, *datasetId) {
	uuYcDatasetParseId(*datasetId, *datasetComponents);
	*wave = *datasetComponents."wave";
	*experimentType = *datasetComponents."experiment_type";
	*pseudocode = *datasetComponents."pseudocode";
	*version = *datasetComponents."version";
	msiGetIcatTime(*date, "unix");
	msiAddKeyVal(*kv, "wave", *wave);
	msiAddKeyVal(*kv, "experiment_type", *experimentType);
	msiAddKeyVal(*kv, "pseudocode", *pseudocode);
	msiAddKeyVal(*kv, "version", *version);
	msiAddKeyVal(*kv, "dataset_date_created", *date);
	msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
}

uuYcVaultWalkRemoveObject(*itemParent, *itemName, *itemIsCollection, *buffer, *status) {
#	writeLine("serverLog", "...removing *itemParent/*itemName");
	if (*itemIsCollection) {
		msiRmColl("*itemParent/*itemName", "forceFlag=", *status);
	} else {
		msiDataObjUnlink("objPath=*itemParent/*itemName++++forceFlag=", *status);
	}
}


uuYcVaultIngestObject(*objectPath, *isCollection, *vaultPath, *status) {
	# from the original object only the below list '*copiedMetadata' of metadata keys 
	# is copied to the vault object, other info is ignored
	*copiedMetadata = list("wave", "experiment_type", "pseudocode", "version",
									 "error", "warning", "comment", "dataset_error",
									 "dataset_warning", "datasetid");
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
				# add relevant kvlist to vault collection object
				foreach (*meta in *copiedMetadata) {
					if (*key == *meta) {
						msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
					}
				}
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
		msiDataObjCopy(*objectPath, *vaultPath, "verifyChksum=", *status);
		if (*status == 0) {
			uuChopPath(*objectPath, *collection, *dataName);
			foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
								      WHERE COLL_NAME = '*collection'
								        AND DATA_NAME = '*dataName'
			) {
				msiGetValByKey(*row, "META_DATA_ATTR_NAME", *key);
				msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *value);
				# add relevant kvlist to vault collection object
				msiString2KeyValPair("*key=*value",*kv);
				foreach (*meta in *copiedMetadata) {
					if (*key == *meta) {
						msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-d");
					}
				}
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
				# Skip duplicas
				break;
			}
		}
	}
}



uuYcVaultWalkIngestObject(*itemParent, *itemName, *itemIsCollection, *buffer, *status) {
	*sourcePath = "*itemParent/*itemName";
	*destPath = *buffer."destination"; # top level destination is specified 
	if (*sourcePath != *buffer."source") {
		# rewrite path to copy objects that are located underneath the toplevel collection
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
	}
#	writeLine("serverLog","VLT from = *sourcePath");
#	writeLine("serverLog","VLT to   = *destPath");
	uuYcVaultIngestObject(*sourcePath, *itemIsCollection, *destPath, *status); 
}


uuYcDatasetCollectionMove2Vault(*intakeRoot,*topLevelCollection, *datasetId, *vaultRoot, *status) {
	writeLine("serverLog","\nmoving dataset-typeA *datasetId from *topLevelCollection to vault");
	*status = 0;
	uuYcVaultDatasetExists(*vaultRoot, *datasetId, *exists);
	if (!*exists) {
		uuYcVaultDatasetGetPath(*vaultRoot, *datasetId, *vaultPath);
		# create the in-between levels of the path to the toplevel collection
		uuChopPath(*vaultPath, *vaultParent, *vaultCollection);
		msiCollCreate(*vaultParent, "1", *status);		
#		writeLine("serverLog","VAULT: dataset created *datasetId status=*status path=*vaultPath");
		if (*status == 0) {
			# copy the dataset tree to the vault
			uuChopPath(*topLevelCollection, *intakeParent, *intakeCollection);
			*buffer."source" = *topLevelCollection;
			*buffer."destination" = *vaultPath;
#			writeLine("serverLog","VAULT: source = *topLevelCollection");
#			writeLine("serverLog","VAULT: dest   = *vaultPath");
			uuTreeWalk(
				"forward", 
				*topLevelCollection,
				"uuYcVaultWalkIngestObject",
				*buffer,
				*status
				);
                       uuKvClear(*buffer);
			if (*status == 0) {
				# stamp the vault dataset collection with additional metadata
				msiGetIcatTime(*date, "unix");
				msiAddKeyVal(*kv, "dataset_date_created", *date);
				msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
				msiModAVUMetadata("-C", *vaultPath, "add", "irods::indexing::index", "yoda::metadata", "elasticsearch");
				# and finally remove the dataset original in the intake area
				msiRmColl(*topLevelCollection, "forceFlag=", *error);
#				uuTreeWalk(
#					"reverse", 
#					*topLevelCollection, 
#					"uuYcVaultWalkRemoveObject", 
#					*buffer, 
#					*error
#					);
				if (*error != 0) {
					writeLine("serverLog",
						"ERROR: unable to remove intake collection *topLevelCollection");
				}
			} else {
				# move failed (partially), cleanup vault
				# NB: keep the dataset in the vault queue so we can retry some other time
				writeLine("serverLog","ERROR: Ingest failed for *datasetId error = *status");
				uuTreeWalk("reverse", *vaultPath, "uuYcVaultWalkRemoveObject", *buffer, *error);
			}

		}
	} else {
		writeLine("serverLog","INFO: version already exists in vault: *datasetId");
		# duplicate dataset, signal error and throw out of vault queue
		*message = "Duplicate dataset, version already exists in vault";
		uuYcDatasetErrorAdd(*intakeRoot, *datasetId,*message);
		uuYcDatasetMelt(*topLevelCollection, *datasetId, *status);
		uuYcDatasetUnlock(*topLevelCollection, *datasetId, *status);
		*status = 1; # duplicate dataset version error
	}
}

uuYcDatasetObjectsOnlyMove2Vault(*intakeRoot, *topLevelCollection, *datasetId, *vaultRoot, *status) {
	writeLine("serverLog","\nmoving dataset-typeB *datasetId from *topLevelCollection to vault");
	uuYcVaultDatasetExists(*vaultRoot, *datasetId, *exists);
	if (!*exists) {
		# new dataset(version) we can safely ingest into vault
		uuYcVaultDatasetGetPath(*vaultRoot, *datasetId, *vaultPath);
		# create path to and including the toplevel collection (will create in-between levels)
		msiCollCreate(*vaultPath, "1", *status);
#		writeLine("serverLog","VAULT: dataset created *datasetId status=*status path=*vaultPath");
		if (*status == 0) {
			# stamp the vault dataset collection with default metadata
			uuYcVaultDatasetAddMeta(*vaultPath, *datasetId);
			# copy data objects to the vault
			foreach (*dataRow in SELECT DATA_NAME
						WHERE COLL_NAME = '*topLevelCollection'
						  AND META_DATA_ATTR_NAME = 'dataset_toplevel'
						  AND META_DATA_ATTR_VALUE = '*datasetId'
				) {
				msiGetValByKey(*dataRow, "DATA_NAME", *dataName);
				*intakePath = "*topLevelCollection/*dataName";
				uuYcVaultIngestObject(*intakePath, false, "*vaultPath/*dataName", *status);
				if (*status != 0) {
					break;
				}
			}
			if (*status == 0) {
				# data ingested, what's left is to delete the original in intake area
				# this will also melt/unfreeze etc because metadata is removed too
				foreach (*dataRow in SELECT DATA_NAME
						WHERE COLL_NAME = '*topLevelCollection'
						  AND META_DATA_ATTR_NAME = 'dataset_toplevel'
						  AND META_DATA_ATTR_VALUE = '*datasetId'
				) {
					msiGetValByKey(*dataRow, "DATA_NAME", *dataName);
					*intakePath = "*topLevelCollection/*dataName";
#					writeLine("serverLog","removing intake file: *intakePath");
					msiDataObjUnlink("objPath=*intakePath++++forceFlag=", *error);
					if (*error != 0) {
						writeLine("serverLog","ERROR: unable to remove intake object *intakePath");
					}
				}
			} else {
				# error occurred during ingest, cleanup vault area and relay the error to user
				# NB: keep the dataset in the vault queue so we can retry some other time
				writeLine("serverLog","ERROR: Ingest failed for *datasetId error = *status");
				*buffer = "required yet dummy parameter";
				uuTreeWalk("reverse", *vaultPath, "uuYcVaultWalkRemoveObject", *buffer, *error);
			}
		}
	} else {
		# duplicate dataset, signal error and throw out of vault queue
		writeLine("serverLog","INFO: version already exists in vault: *datasetId");
		*message = "Duplicate dataset, version already exists in vault";
		uuYcDatasetErrorAdd(*intakeRoot, *datasetId,*message);
		uuYcDatasetMelt(*topLevelCollection, *datasetId, *status);
		uuYcDatasetUnlock(*topLevelCollection, *datasetId, *status);
		*status = 1; # duplicate dataset version error
	}
}



# \brief move all locked datasets to the vault
#
# \param[in]  intakeCollection  pathname root of intake area
# \param[in]  vaultCollection   pathname root of vault area
# \param[out] status            result of operation either "ok" or "error"
#
uuYc2Vault(*intakeRoot, *vaultRoot, *status) {
	# 1. add to_vault_freeze metadata lock to the dataset
	# 2. check that dataset does not yet exist in the vault
	# 3. copy dataset to vault with its metadata
	# 4. remove dataset from intake
	# upon any error:
	# - delete partial data from vault
	# - add error to intake dataset metadata
	# - remove locks on intake dataset (to_vault_freeze, to_vault_lock)
	*status = 0; # 0 is success, nonzero is error
	*datasets_moved = 0;

	# note that we have to allow for multiple types of datasets:
	#    type A: a single toplevel collection with a tree underneath
	#    type B: one or more datafiles located within the same collection
	# processing varies slightly between them, so process each type in turn
	#
	# TYPE A:
	foreach (*row in SELECT COLL_NAME, META_COLL_ATTR_VALUE
				WHERE META_COLL_ATTR_NAME = 'dataset_toplevel'
				  AND COLL_NAME like '*intakeRoot/%') {
		msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *datasetId);
		uuYcObjectIsLocked(*topLevelCollection, true, *locked, *frozen);
		if (*locked) {
			uuYcDatasetFreeze(*topLevelCollection, *datasetId, *status);
			if (*status == 0) {
				# datset frozen, now move to fault and remove from intake area
				uuYcDatasetCollectionMove2Vault(
						*intakeRoot, 
						*topLevelCollection,
						*datasetId,
						*vaultRoot,
						*status
						);
				if (*status == 0) {
					*datasets_moved = *datasets_moved + 1;
				}
			}
		}
	}
	# TYPE B:
	foreach (*row in SELECT COLL_NAME, META_DATA_ATTR_VALUE
				WHERE META_DATA_ATTR_NAME = 'dataset_toplevel'
				  AND COLL_NAME like '*intakeRoot%'
# fixme: skip collnames that are not in the same tree yet share the prefix
				) {

		msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
		msiGetValByKey(*row, "META_DATA_ATTR_VALUE", *datasetId);
		# check if to_vault_lock exists on all the dataobjects of this dataset
		*allLocked = true;
		foreach (*dataRow in SELECT DATA_NAME
						WHERE COLL_NAME = '*topLevelCollection'
						  AND META_DATA_ATTR_NAME = 'dataset_toplevel'
						  AND META_DATA_ATTR_VALUE = '*datasetId'
			) {
			msiGetValByKey(*dataRow, "DATA_NAME", *dataName);
			uuYcObjectIsLocked("*topLevelCollection/*dataName", false, *locked, *frozen);
			*allLocked = *allLocked && *locked;
		}
		if (*allLocked) {
			uuYcDatasetFreeze(*topLevelCollection, *datasetId, *status);
			if (*status == 0) {
				# dataset frozen, now move to fault and remove from intake area
				uuYcDatasetObjectsOnlyMove2Vault(
					*intakeRoot,
					*topLevelCollection,
					*datasetId,
					*vaultRoot,
					*status
					);
				if (*status == 0) {
					*datasets_moved = *datasets_moved + 1;
				}
			}
		}
	}
	if (*datasets_moved > 0) {
		writeLine("serverLog","\nmoved in total *datasets_moved dataset(s) to the vault");
	}
}

#input null
#output ruleExecOut
