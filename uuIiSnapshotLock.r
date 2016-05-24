# \file
# \brief lock/freeze and unlock/unfreeze datasets within a collection
#			for sending to dataset. Based on ycDatasetLock (may 11 2016)
# \author Jan de Mooij
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#

# \brief iiDatasetSnapshotLockChangeObject Changes the lock state of an 
#					object based on the parameters that it is given.
#					Adapted from uuYcDatasetLockChangeObject to allow for
#					to_snapshot_lock and to_snapshot_freeze, which should copy
#					a dataset / object, rather than move it
#
# \param[in] parentCollection 	The COLL_NAME of the collection this object 
#								resides in
# \param[in] objectName 		Name of the target object
# \param[in] isCollection 		Bool, true iff target object is a collection
# \param[in] lockName			Key name of the meta data object that is added
# \param[in] lockIt 			Boolean, true iff the object should be locked.
# 									if false, the lock is removed (if allowed)
# \param[in] Datetime			The value that is given to the meta data object,
#									if lockIt is true
# \param[out] result 			Exit code. Non-zero means error. See code for 
#									where this might have gone wrong.
iiDatasetSnapshotLockChangeObject(*parentCollection, *objectName, *isCollection,
						 *lockName, *lockIt, *dateTime, *result) {
	*objectType = "-d";
	*path = "*parentCollection/*objectName";
	if (*isCollection) {
		*objectType = "-C";
		*collection = *objectName;
	}
	if (*lockIt) {
		msiString2KeyValPair("*lockName=*dateTime",*kvPair);
		*result = errorcode(msiSetKeyValuePairsToObj(*kvPair, *path, *objectType));
	} else {  # unlock it
		#
		# if the lock is of type to_vault_lock this operation is
		# disallowed if the object also has a to_vault_freeze lock
		iiObjectIsSnapshotLocked(*path,*isCollection,*locked,*frozen);
		*allowed = (*lockName == "to_vault_freeze" || *lockName == "to_snapshot_freeze") || !*frozen;
		if (*allowed) {
			*result = 0;
			# in order to remove the key we need to lookup its value(s)
			if (*isCollection) {
				# remove lock from collection
				foreach (*row in SELECT META_COLL_ATTR_VALUE
									WHERE COLL_NAME = '*path'
									  AND META_COLL_ATTR_NAME = '*lockName') {
					msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
					msiString2KeyValPair("*lockName=*value", *kvPair);
					*result = errorcode(
								msiRemoveKeyValuePairsFromObj(*kvPair, *path, "-C")
								);
					if (*result != 0) {
						*result = -51;
						break;
					}
				}
			} else {
				# remove lock from data object
				foreach (*row in SELECT META_DATA_ATTR_VALUE
								WHERE DATA_NAME = '*objectName'
								  AND COLL_NAME = '*parentCollection'
								  AND META_DATA_ATTR_NAME = '*lockName'
					) {
					msiGetValByKey(*row,"META_DATA_ATTR_VALUE",*value);
					msiString2KeyValPair("*lockName=*value",*kvPair);
					*result = errorcode(
								msiRemoveKeyValuePairsFromObj(
										*kvPair,
										"*parentCollection/*objectName",
										"-d"
									)
								);
					if (*result != 0) {
						*result = -52;
						break;
					}
				}
			} # end else remove lock from dataobject
		} else { # unlock not allowed
			*result = -61;
		}
	}
}


iiDatasetWalkSnapshotVaultLock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	iiDatasetSnapshotLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_snapshot_lock", true, *dateTime, *error);
}

iiDatasetWalkSnapshotVaultUnlock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	iiDatasetSnapshotLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_snapshot_lock", false, *dateTime, *error);
}

iiDatasetWalkSnapshotFreezeLock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	iiDatasetSnapshotLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_snapshot_freeze", true, *dateTime, *error);
}


iiDatasetWalkSnapshotFreezeUnlock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	iiDatasetSnapshotLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_snapshot_freeze", false, *dateTime, *error);
}

# \brief iiDatasetSnapshotLockChange 	Adapted from uuYcDatasetLockChange to
#					allow for to_snapshot_lock and to_snapshot_freeze. Logic is
#					slightly altered to allow more values
#
# \param[in] rootCollection 	The COLL_NAME of the collection the dataset resides in
# \param[in] datasetId 			The name of the dataset directory (dirname only, not 
#									the entire collection name)
# \param[in] lockName			Key name of the meta data object that is added
# \param[in] lockIt 			Boolean, true iff the object should be locked.
# 									if false, the lock is removed (if allowed)
# \param[out] status 			Zero if no errors, non-zero otherwise
iiDatasetSnapshotLockChange(*rootCollection, *datasetId, *lockName, *lockIt, *status){
   	*set="uuYc";
   	*lockProcedure = "Vault";
   	*vault="";
   	if(*lockName == "to_snapshot_freeze" || *lockName == "to_snapshot_lock") {
   		*set = "ii";
   		*vault="Snapshot";
   	}
	*lock = "Unlock";
	if (*lockIt) {
		*lock = "Lock";
	}
	if (*lockName == "to_vault_freeze" || *lockName == "to_snapshot_freeze") {
		*lockProcedure = "Freeze";
	} 
	*buffer = "dummy";
	uuTreeWalk("forward", "*rootCollection/*datasetId", "*set" ++ "DatasetWalk" ++ "*vault*lockProcedure*lock", *buffer, *error);
	*status = str(*error);
}

# \brief uuYcDatasetLock locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
iiDatasetSnapshotLock(*collection, *datasetId, *status) {
	iiDatasetSnapshotLockChange(*collection, *datasetId,"to_snapshot_lock", true, *status);

	# Set meta data value to indicate this is the toplevel of the dataset that
	# was prepared for snapshotting
	if(*status == 0) {
		msiGetIcatTime(*dateTime,"unix");
		msiString2KeyValPair("dataset_snapshotlock_toplevel=*dateTime:$rodsZoneClient#$userNameClient", *kvPair);
		*status = errorcode(
			msiSetKeyValuePairsToObj(*kvPair, "*collection/*datasetId", "-C")
		);
	}
}

# \brief iiDatasetSnapshotUnlock  unlocks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] result     "true" upon success, otherwise "false"
# \param[out] status     0 upon success, otherwise nonzero
#
iiDatasetSnapshotUnlock(*collection, *datasetId, *status) {
	iiDatasetSnapshotLockChange(*collection, *datasetId, "to_snapshot_lock", false, *status);


	# Remove meta data value that was set to indicate this is the toplevel 
	# of the dataset that was prepared for snapshotting
	if(*status == 0){
		foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE META_COLL_ATTR_NAME = 'dataset_snapshotlock_toplevel'
			AND COLL_NAME = "*collection/*datasetId") {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			msiString2KeyValPair("dataset_snapshotlock_toplevel=*value", *kvPair);
			*status = errorcode(
					msiRemoveKeyValuePairsFromObj(*kvPair, "*collection/*datasetId", "-C")
				)
		}
	}
}

# \brief iiDatasetSnapshotFreeze  freeze-locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
iiDatasetSnapshotFreeze(*collection, *datasetId, *status) {
	iiDatasetSnapshotLockChange(*collection, *datasetId,"to_snapshot_freeze", true, *status);
}

# \brief iiDatasetSnapshotMelt  undo freeze-locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
iiDatasetSnapshotMelt(*collection, *datasetId, *status) {
	iiDatasetSnapshotLockChange(*collection, *datasetId, "to_snapshot_freeze", false, *status);
}

# \brief iiObjectIsSnapshotLocked  query an object to see if it is locked
#
# \param[in]  objectPath    full path to collection of data object
# \param[in]  isCollection  true if path references a collection
# \param[out] locked        true if the object is vault-locked
# \param[out] frozen        true if the object is vault-frozen
#
iiObjectIsSnapshotLocked(*objectPath, *isCollection, *locked, *frozen) {
	*locked = false;
	*frozen = false;
	if (*isCollection) {
		foreach (*row in SELECT META_COLL_ATTR_NAME
			WHERE COLL_NAME = '*objectPath'
		) {
			msiGetValByKey(*row, "META_COLL_ATTR_NAME", *key);
			if( *key == "to_snapshot_lock" || *key == "to_vault_lock" || *key == "to_vault_freeze" || *key == "to_snapshot_freeze") {
				*locked = true;
				if (*key == "to_snapshot_freeze" || *key == "to_vault_freeze") {
					*frozen = true;
					break;
				}
			}
		}
	} else {
		uuChopPath(*objectPath, *parentCollection, *dataName);
		foreach (*row in SELECT META_DATA_ATTR_NAME
					WHERE COLL_NAME = '*parentCollection'
					  AND DATA_NAME = '*dataName'
			) {
			msiGetValByKey(*row, "META_DATA_ATTR_NAME", *key);
			if (   *key == "to_snapshot_lock"
				 || *key == "to_snapshot_freeze" 
				 || *key == "to_vault_lock" 
				 || *key == "to_vault_freeze"
				 ) {
				*locked = true;
				if (*key == "to_snapshot_freeze"  || *key == "to_vault_freeze") {
					*frozen = true;
					break;
				}
			}
		}
	}
}