# \file
# \brief lock/freeze and unlock/unfreeze datasets within a collection
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#

#test {
#*collection = "/nluu1ot/home/ton";
#*datasetId = "y";
#uuYcDatasetLock(*collection, *datasetId, *result);
#writeLine("stdout","lock result = *result");
#uuYcDatasetFreeze(*collection, *datasetId, *result);
#writeLine("stdout","freeze result = *result");
#uuYcObjectIsLocked("*collection/Newfile.txt",false, *locked, *frozen);
#writeLine("stdout","locked = *locked  and frozen = *frozen");

#uuYcDatasetUnlock(*collection, *datasetId, *result);
#writeLine("stdout","unlock result = *result");
#uuYcDatasetMelt(*collection, *datasetId, *result);
#writeLine("stdout","melt result = *result");
#uuYcDatasetUnlock(*collection, *datasetId, *result);
#writeLine("stdout","unlock result = *result");
#}

uuYcDatasetLockChangeObject(*parentCollection, *objectName, *isCollection,
						 *lockName, *lockIt, *dateTime,*result) {
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
		uuYcObjectIsLocked(*path,*isCollection,*locked,*frozen);
		*allowed = (*lockName == "to_vault_freeze") || !*frozen;
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
						break;
					}
				}
			} # end else remove lock from dataobject
		} else { # unlock not allowed
			*result = -1;
		}
	}
}

uuYcDatasetWalkVaultLock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	uuYcDatasetLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_vault_lock", true, *dateTime, *error);
}

uuYcDatasetWalkVaultUnlock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	uuYcDatasetLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_vault_lock", false, *dateTime, *error);
}

uuYcDatasetWalkFreezeLock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	uuYcDatasetLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_vault_freeze", true, *dateTime, *error);
}


uuYcDatasetWalkFreezeUnlock(*itemCollection, *itemName, *itemIsCollection, *buffer, *error) {
	msiGetIcatTime(*dateTime,"unix");
	uuYcDatasetLockChangeObject(*itemCollection, *itemName, *itemIsCollection,
						 "to_vault_freeze", false, *dateTime, *error);
}


uuYcDatasetLockChange(*rootCollection, *datasetId, *lockName, *lockIt, *status){
   *status = -1;
	*lock = "Unlock";
	if (*lockIt) {
		*lock = "Lock";
	}
	*lockProcedure = "Vault";
	if (*lockName == "to_vault_freeze") {
		*lockProcedure = "Freeze";
	}
	# find the toplevel collection for this dataset
	uuYcDatasetGetTopLevel(*rootCollection, *datasetId, *collection, *isCollection);
	if (*collection != "") {
		# we found the dataset, now change the lock on each object
		if (*isCollection) {
			*buffer = "dummy";
			uuTreeWalk("forward", *collection, "uuYcDatasetWalk*lockProcedure*lock", *buffer, *error);
			*status = *error;
#			if (*error == "0") {
#				*status = 0;
#			}
		} else {
			# dataset is not a collection, let's find the objects and make the change
			msiGetIcatTime(*dateTime,"unix");
			*status = 0;
			foreach (*row in SELECT DATA_NAME
						WHERE COLL_NAME = '*collection'
						  AND META_DATA_ATTR_NAME = 'dataset_toplevel'
						  AND META_DATA_ATTR_VALUE = '*datasetId'
				) {
				msiGetValByKey(*row,"DATA_NAME",*dataName);
				# now change it ....
				uuYcDatasetLockChangeObject(
							*collection,
							*dataName,
							false,
							*lockName,
							*lockIt,
							*dateTime,
							*error);
				if (*error != 0 ) {
					*status = *error;
					break;
				}
			}
		}

	} else {
		# result is false "dataset not found"
	}
}


# \brief uuYcDatasetLock locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
uuYcDatasetLock(*collection, *datasetId, *status) {
	uuYcDatasetLockChange(*collection, *datasetId,"to_vault_lock", true, *status);
}

# \brief uuYcDatasetUnlock  unlocks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] result     "true" upon success, otherwise "false"
# \param[out] status     0 upon success, otherwise nonzero
#
uuYcDatasetUnlock(*collection, *datasetId, *status) {
	uuYcDatasetLockChange(*collection, *datasetId, "to_vault_lock", false, *status);
}

# \brief uuYcDatasetFreeze  freeze-locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
uuYcDatasetFreeze(*collection, *datasetId, *status) {
	uuYcDatasetLockChange(*collection, *datasetId,"to_vault_freeze", true, *status);
}

# \brief uuYcDatasetUnfreeze  undo freeze-locks (all objects of) a dataset
#
# \param[in]  collection collection that may have datasets
# \param[in]  datasetId  identifier to depict the dataset
# \param[out] status     0 upon success, otherwise nonzero
#
uuYcDatasetMelt(*collection, *datasetId, *status) {
	uuYcDatasetLockChange(*collection, *datasetId, "to_vault_freeze", false, *status);
}

# \brief uuYcObjectIsLocked  query an object to see if it is locked
#
# \param[in]  objectPath    full path to collection of data object
# \param[in]  isCollection  true if path references a collection
# \param[out] locked        true if the object is vault-locked
# \param[out] frozen        true if the object is vault-frozen

uuYcObjectIsLocked(*objectPath, *isCollection, *locked, *frozen) {
	*locked = false;
	*frozen = false;
	if (*isCollection) {
		foreach (*row in SELECT META_COLL_ATTR_NAME
					WHERE COLL_NAME = '*objectPath'
					) {
			msiGetValByKey(*row, "META_COLL_ATTR_NAME", *key);
			if (   *key == "to_vault_lock"
				 || *key == "to_vault_freeze"
				 ) {
				*locked = true;
				if (*key == "to_vault_freeze") {
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
			if (   *key == "to_vault_lock"
				 || *key == "to_vault_freeze"
				 ) {
				*locked = true;
				if (*key == "to_vault_freeze") {
					*frozen = true;
					break;
				}
			}
		}
	}
}

#input null
#output ruleExecOut
