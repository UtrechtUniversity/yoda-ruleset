uuIiGetGroupPrefix(*grpPrefix) {
	*grpPrefix = "grp-"
}
uuIiGetIntakePrefix(*intakePrefix) {
	uuIiGetGroupPrefix(*grp);
	*intakePrefix = *grp
}
uuIiGetVaultPrefix(*vaultPrefix) {
	uuIiGetGroupPrefix(*grp);
	*vaultPrefix = "vault-";
}
uuIiGetMetadataPrefix(*metadataPrefix) {
	*metadataPrefix = "ilab_";
}
uuIiVersionKey(*versionKey, *dependsKey) {
	uuIiGetMetadataPrefix(*prfx);
	*versionKey = *prfx ++ "version";
	*dependsKey = *prfx ++ "depends_on";
}
GENQMAXROWS = 256
IIGROUPPREFIX = "research-"
IIXSDCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsd"
IIXSLCOLLECTION = UUSYSTEMCOLLECTION ++ "/xsl"
IIFORMELEMENTSCOLLECTION = UUSYSTEMCOLLECTION ++ "/formelements"
IIXSDDEFAULTNAME = "default.xsd"
IIFORMELEMENTSDEFAULTNAME = "default.xml"
IIMETADATAXMLNAME = "yoda-metadata.xml"
IIXSLDEFAULTNAME = "default.xsl"
IIVALIDLOCKS = list("protect", "submit", "tovault");
UNPROTECTED = "UNPROTECTED"
PROTECTED = "PROTECTED"
SUBMITTED = "SUBMITTED"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
ARCHIVED = "ARCHIVED"
IIFOLDERSTATES = list(UNPROTECTED, PROTECTED, SUBMITTED, APPROVED, REJECTED, ARCHIVED);
IIFOLDERTRANSITIONS = list((UNPROTECTED, PROTECTED),
			   (UNPROTECTED, SUBMITTED),
			   (PROTECTED, UNPROTECTED),
			   (PROTECTED, SUBMITTED),
			   (SUBMITTED, APPROVED),
			   (SUBMITTED, REJECTED),
			   (REJECTED, UNPROTECTED),
			   (APPROVED, ARCHIVED),
			   (ARCHIVED, UNPROTECTED));
iiFileCount(*path, *totalSize, *dircount, *filecount, *modified) {
    *dircount = "0";
    *filecount = "0";
    *totalSize = "0";
    *data_modified = "0";
    *coll_modified = "0";
    msiMakeGenQuery("sum(DATA_SIZE), count(DATA_ID), max(DATA_MODIFY_TIME)", "COLL_NAME like '*path%'", *GenQInp);
    msiExecGenQuery(*GenQInp, *GenQOut);
    foreach(*GenQOut) {
        msiGetValByKey(*GenQOut, "DATA_SIZE", *totalSize);
        msiGetValByKey(*GenQOut, "DATA_ID", *filecount);
        msiGetValByKey(*GenQOut, "DATA_MODIFY_TIME", *data_modified);
        break;
    }
    msiMakeGenQuery("count(COLL_ID), max(COLL_MODIFY_TIME)", "COLL_NAME like '*path%'", *GenQInp2);
    msiExecGenQuery(*GenQInp2, *GenQOut2);
    foreach(*GenQOut2) {
        msiGetValByKey(*GenQOut2, "COLL_ID", *dircount);
        msiGetValByKey(*GenQOut2, "COLL_MODIFY_TIME", *coll_modified);
        break;
    }
    *data_modified = int(*data_modified);
    *coll_modified = int(*coll_modified);
    *modified = str(max(*data_modified, *coll_modified));
}
iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager) {
	*isfound = false;
	*groupName = "";
	foreach(*accessid in SELECT COLL_ACCESS_USER_ID WHERE COLL_NAME = *path) {
		*id = *accessid.COLL_ACCESS_USER_ID;
		foreach(*group in SELECT USER_GROUP_NAME WHERE USER_GROUP_ID = *id) {
				*groupName = *group.USER_GROUP_NAME;
		}
		if (*groupName like regex "(research|intake)-.*") {
			*isfound = true;
			break;
		}
	}
	writeLine("serverLog", "iiCollectionGroupNameAndUserType: groupName = *groupName");
	if (!*isfound) {
		failmsg(-808000, "path does not belong to a research or intake group or is not available to current user");
	}
	uuGroupGetMemberType(*groupName, uuClientFullName, *userType);
	uuGroupGetCategory(*groupName, *category, *subcategory);	
	uuGroupGetMemberType("datamanager-" ++ *category, uuClientFullName, *userTypeIfDatamanager);
	if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
		*isDatamanager = true;
	} else {
		*isDatamanager = false;
	}	
	writeLine("serverLog", "iiCollectionGroupNameAndUserType: userType = *userType, isDatamanager = *isDatamanager");
}
uuIi2Vault(*intakeRoot, *vaultRoot, *status) {
	*status = 0; # 0 is success, nonzero is error
	foreach (*row in SELECT COLL_NAME, META_COLL_ATTR_VALUE
				WHERE META_COLL_ATTR_NAME = 'dataset_snapshotlock_toplevel'
				  AND COLL_NAME like '*intakeRoot/%') {
		msiGetValByKey(*row, "COLL_NAME", *topLevelCollection);
		uuChopPath(*topLevelCollection, *parent, *datasetId);
		iiObjectIsSnapshotLocked(*topLevelCollection, true, *locked, *frozen);
		*recover = false;
		if (*locked) {
			uuLock(*topLevelCollection, *lockStatus);
			if(*lockStatus == 0) {
				iiDatasetSnapshotFreeze(*topLevelCollection, *status) ::: *recover = true;
				msiGetIcatTime(*time, "human");
				writeLine("stdout", "[*time] Finished freezing dataset");
				uuIiDatasetCollectionCopy2Vault(
						*intakeRoot, 
						*topLevelCollection,
						*datasetId,
						*vaultRoot,
						*status
					) ::: *recover = true;
				msiGetIcatTime(*time, "human");
				writeLine("stdout", "[*time] Finished copying collection with status *status");
				if(*status == 0) {
					iiDatasetSnapshotMelt(*topLevelCollection, *statusm) ::: *recover = true;
					msiGetIcatTime(*time, "human");
					writeLine("stdout", "[*time] Finished melting *topLevelCollection with status *statusm");
					iiDatasetSnapshotUnlock(*topLevelCollection, *statusu) ::: *recover = true;
					msiGetIcatTime(*time, "human");
					writeLine("stdout", "[*time] Finished unlocking *topLevelCollection with status *statusu");
				} else {
					writeLine("stdout", "[*time] Copying to vault exited with code *status. Now melting.");
					iiDatasetSnapshotMelt(*topLevelCollection, *status) ::: *recover = true;
					msiGetIcatTime(*time, "human");
					writeLine("stdout", "[*time] Finished melting after error on creating version *topLevelCollection with status *status");
				}
				uuUnlock(*topLevelCollection);
			}
		}
		if(*recover) {
			msiGetIcatTime(*time, "human");
			writeLine("stdout", "[*time] Recovering *topLevelCollection");
			uuUnlock(*topLevelCollection)
		}
	}
}
uuIiAddSnapshotInformationToVault(*vaultPath, *status) {
	*snapshotInfoKey = "snapshot_version_information";
	msiGetIcatTime(*time, "human");
	writeLine("stdout", "[*time] Setting snapshot information");
	uuIiVersionKey(*versionKey, *dependsKey);
	writeLine("stdout", "[*time] Vault path is '*vaultPath");
	msiMakeGenQuery(
		"META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
		"COLL_NAME = '*vaultPath' AND META_COLL_ATTR_NAME in ('*versionKey', '*dependsKey', 'dataset_snapshotlock_toplevel')",
		*versionAndDependsQuery
	);
	msiExecGenQuery(*versionAndDependsQuery, *versionAndDependsOut);
	*version = "";
	*depends = "";
	*userZone = "";
	*created = "";
	foreach(*versionAndDependsOut) {
		msiGetValByKey(*versionAndDependsOut, "META_COLL_ATTR_NAME", *name);
		msiGetValByKey(*versionAndDependsOut, "META_COLL_ATTR_VALUE", *value);
		if(*name == *versionKey) {
			*version = *value;
		} else if(*name == *dependsKey) {
			*depends = *value;
		} else if(*name == "dataset_snapshotlock_toplevel") {
			*created = trimr(*value, ":");
			*userZone = triml(*value, ":");
		}
	}
	*dependsVersion = "";
	*dependsCollName = "";
	if(*depends != "") {
		foreach(*row in SELECT COLL_NAME, META_COLL_ATTR_VALUE 
			WHERE COLL_ID = '*depends' 
			AND META_COLL_ATTR_NAME = '*versionKey'
		) {
			msiGetValByKey(*row, "COLL_NAME", *dependsCollName);
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *dependsVersion);
		}
	}
	*snapshotInfo = "*version#*created#*userZone#*depends#*dependsCollName#*dependsVersion";
	msiAddKeyVal(*kv, *snapshotInfoKey, *snapshotInfo);
	*status = errorcode(msiSetKeyValuePairsToObj(*kv, *vaultPath, "-C"));
}
uuIiAddSnapshotLogToCollection(*collection, *status) {
	msiGetIcatTime(*time, "human");
	writeLine("stdout", "[*time] Creating a log entry after a succesful new version creation for *collection");
	uuIiVersionKey(*versionKey, *dependsKey);
	*value = "";
	*version = "";
	*depends = "";
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE
		COLL_NAME = "*collection"
	) {
		if(*row.META_COLL_ATTR_NAME == 'dataset_snapshotlock_toplevel') {
			*value = *row.META_COLL_ATTR_VALUE;
		} else if(*row.META_COLL_ATTR_NAME == '*versionKey') {
			*version = *row.META_COLL_ATTR_VALUE;
		} else if(*row.META_COLL_ATTR_NAME == '*dependsKey') {
			*depends = *row.META_COLL_ATTR_VALUE;
		}
	}
	*logMessage = "*version:*depends:*value";
	msiString2KeyValPair("dataset_snapshot_createdAtBy=*logMessage", *kvPair);
	*status = errorcode(
		msiAssociateKeyValuePairsToObj(*kvPair, "*collection", "-C")
	);
	writeLine("stdout", "[*time] Finished updating createdAtBy (*value) with status *status");
}
uuIiDatasetCollectionCopy2Vault(*intakeRoot, *topLevelCollection, *datasetId, *vaultRoot, *status) {
	*status = 0;
	msiGetIcatTime(*time, "human");
	iiCollectionExists(*vaultRoot, *vaultRootExists);
	if(*vaultRootExists) {
		uuIiVaultSnapshotGetPath(*vaultRoot, *topLevelCollection, *vaultPath);
		iiCollectionExists(*vaultPath, *exists);
		if (!*exists) {
			uuChopPath(*vaultPath, *vaultParent, *vaultCollection);
			*status = errorcode(msiCollCreate(*vaultParent, "1", *status));	
			if (*status >= 0) {
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
					msiGetIcatTime(*time, "human");
					uuIiCopyParentsMetadata(*topLevelCollection, *vaultPath, *parentMetaStatus)::: writeLine("stdout", "[*time] Could not copy parents metadata of *topLevelCollection to *vaultPath");
					uuIiUpdateVersion(*topLevelCollection, *vaultPath, *versionBumbStatus)::: writeLine("stdout", "[*time] Could not bump version of *topLevelCollection");
					uuIiAddSnapshotInformationToVault(*vaultPath, *snapInfoStatus) ::: writeLine("stdout", "[*time] Could not update snapshot information to *vaultPath");
					msiGetIcatTime(*date, "unix");
					msiAddKeyVal(*kv, "snapshot_date_created", *date);
					msiAssociateKeyValuePairsToObj(*kv, *vaultPath, "-C");
					uuChopPath(*vaultPath, *vaultDatasetRoot, *vaultBase)
					iiDatasetSnapshotMelt(*vaultPath, *status);
					iiDatasetSnapshotUnlock(*vaultPath, *status);
					uuUnlock(*vaultPath);
				} else {
					writeLine("stdout","[*time] ERROR: Ingest failed for *datasetId error = *status");
					uuTreeWalk("reverse", *vaultPath, "iiVaultWalkRemoveObject", *buffer, *error) ::: writeLine("stdout", "[*time] Failed reversing *vaultPath");
				}
			}
		} else {
			writeLine("stdout","[*time] INFO: version already exists in vault: *datasetId");
			*message = "Duplicate dataset, version already exists in vault";
			iiDatasetSnapshotMelt(*topLevelCollection, *status);
			iiDatasetSnapshotUnlock(*topLevelCollection, *status);
			*status = 1; # duplicate dataset version error
		}
	} else {
		writeLine("stdout", "[*time] INFO: Vault root *vaultRoot does not exist. Snapshot failed");
		*message = "Vault root *vaultRoot does not exist.";
		iiDatasetSnapshotMelt(*topLevelCollection, *status);
		iiDatasetSnapshotUnlock(*topLevelCollection, *status);
		*status = 1; # duplicate dataset version error
	}
}
uuIiCopyParentsMetadata(*topLevelCollection, *vaultPath, *status) {
	msiGetIcatTime(*time, "human");
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
				*msg = "[*time] WARNING: Something went wrong in extracing or updating the medatadata";
				*msg = "*msg from '*parent'. The extracted key was '*key' and the extracted value was '*value'";
				writeLine("stdout", *msg);
				*status = -100;
			}
		}
		uuChopPath(*parent, *parent_new, *base);
		*parent = *parent_new;
	}
}
uuIiUpdateVersion(*topLevelCollection, *vaultPath, *status) {
	msiGetIcatTime(*time, "human");
	uuIiVersionKey(*versionKey, *dependsKey);
	*version = 1;
	*depends = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE 
		COLL_NAME = "*topLevelCollection" AND 
		META_COLL_ATTR_NAME = "*versionKey"
	) {
		msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
		writeLine("stdout", "[*time] Found version *value");
		*version = int(*value) + 1;
		writeLine("stdout", "[*time] ew version is *version");
		break;
	}
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = "*vaultPath") {
		msiGetValByKey(*row, "COLL_ID", *depends);
		break;
	}
	writeLine("stdout", "[*time] Going to set version to *version, and depends to *depends");
	msiAddKeyVal(*kv, *versionKey, str(*version));
	msiAddKeyVal(*kv, *dependsKey, *depends);
    *status = errorcode(msiSetKeyValuePairsToObj(*kv, *topLevelCollection, "-C"));
    writeLine("stdout", "[*time] Finished updating version with status *status");
}
uuIiVaultWalkIngestObject(*itemParent, *itemName, *itemIsCollection, *buffer, *status) {
	*sourcePath = "*itemParent/*itemName";
	*destPath = *buffer."destination"; # top level destination is specified 
	if (*sourcePath != *buffer."source") {
		*sourceLength = strlen(*sourcePath);
		*relativePath = substr(*sourcePath, strlen(*buffer."source") + 1, *sourceLength);
		*destPath = *buffer."destination" ++ "/" ++ *relativePath;
	}
	uuIiVaultIngestObject(*sourcePath, *itemIsCollection, *destPath, *status); 
}
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
uuIiSnapshotGetVaultParent(*vaultRoot, *topLevelCollection, *vaultParent) {
	*pathStart = "/$rodsZoneClient/home";
	*segmentsWithRoot = substr(*topLevelCollection, strlen(*pathStart), strlen(*topLevelCollection));
	if(*segmentsWithRoot like '/*') {
		*segmentsWithRoot = triml(*segmentsWithRoot, '/');
	}
	uuStrToLower(triml(*segmentsWithRoot, '/'), *segments);
	*vaultParent = "*vaultRoot/*segments";
}
uuIiVaultSnapshotGetPath(*vaultRoot, *topLevelCollection, *vaultPath) {
	msiGetIcatTime(*time, "human");
	*humanTime = trimr(trimr(*time, ":"), ":") ++ "h" ++ triml(trimr(*time, ":"), ":");
	uuIiSnapshotGetVaultParent(*vaultRoot, *topLevelCollection, *vaultParent);
	*vaultPath = "*vaultParent/*humanTime";
}
iiCollectionExists(*collectionName, *exists) {
	*exists = false;
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*collectionName') {
		*exists = true;
		break;
	}
}
uuIiGetVaultrootFromIntake(*intakeRoot, *vaultRoot) {
	uuIiGetIntakePrefix(*intakePrfx);
    uuIiGetVaultPrefix(*vaultPrfx);
    *home = trimr(*intakeRoot, "/");
    *group = substr(*intakeRoot, strlen(*home), strlen(*intakeRoot));
    if(*group like '/*') {
            *group = triml(*group, "/");
    }
    if(*group like '*intakePrfx*') {
            *groupName = substr(*group, strlen(*intakePrfx), strlen(*group));
            *vaultRoot = *home ++ "/" ++ *vaultPrfx ++ *groupName;
    } else {
            *vaultRoot = false;
    }
}
iiVaultWalkRemoveObject(*itemParent, *itemName, *itemIsCollection, *buffer, *status) {
	if (*itemIsCollection) {
		msiRmColl("*itemParent/*itemName", "forceFlag=", *status);
	} else {
		msiDataObjUnlink("objPath=*itemParent/*itemName++++forceFlag=", *status);
	}
}
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
		iiObjectIsSnapshotLocked(*path,*isCollection,*locked,*frozen);
		*allowed = (*lockName == "to_vault_freeze" || *lockName == "to_snapshot_freeze") || !*frozen;
		if (*allowed) {
			*result = 0;
			if (*isCollection) {
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
iiDatasetSnapshotLockChange(*rootCollection, *lockName, *lockIt, *status){
   	*set="uu";
   	*lockProcedure = "Vault";
   	*vault="";
   	if(*lockName == "to_snapshot_freeze" || *lockName == "to_snapshot_lock") {
   		*set = "ii";
   		*vault="Snapshot";
   	}
	*lock = "Unlock";
	*direction = "reverse";
	if (*lockIt) {
		*lock = "Lock";
		*direction = "forward";
	}
	if (*lockName == "to_vault_freeze" || *lockName == "to_snapshot_freeze") {
		*lockProcedure = "Freeze";
	} 
	*buffer = "dummy";
	uuTreeWalk(*direction, "*rootCollection", "*set" ++ "DatasetWalk" ++ "*vault*lockProcedure*lock", *buffer, *error);
	*status = str(*error);
}
iiDatasetSnapshotLock(*collection, *status) {
	iiDatasetSnapshotLockChange(*collection, "to_snapshot_lock", true, *status);
	if(*status == 0) {
		msiGetIcatTime(*dateTime,"unix");
		msiString2KeyValPair("dataset_snapshotlock_toplevel=*dateTime:$userNameClient#$rodsZoneClient", *kvPair);
		*status = errorcode(
			msiSetKeyValuePairsToObj(*kvPair, "*collection", "-C")
		);
	}
}
iiDatasetSnapshotUnlock(*collection, *status) {
	iiDatasetSnapshotLockChange(*collection, "to_snapshot_lock", false, *status);
	if(*status == 0){
		foreach(*row in SELECT META_COLL_ATTR_VALUE 
			WHERE META_COLL_ATTR_NAME = 'dataset_snapshotlock_toplevel'
			AND COLL_NAME = "*collection") {
			msiGetValByKey(*row, "META_COLL_ATTR_VALUE", *value);
			msiString2KeyValPair("dataset_snapshotlock_toplevel=*value", *kvPair);
			*status = errorcode(
					msiRemoveKeyValuePairsFromObj(*kvPair, "*collection", "-C")
				)
		}
	}
}
iiDatasetSnapshotFreeze(*collection, *status) {
	iiDatasetSnapshotLockChange(*collection, "to_snapshot_freeze", true, *status);
}
iiDatasetSnapshotMelt(*collection, *status) {
	iiDatasetSnapshotLockChange(*collection, "to_snapshot_freeze", false, *status);
}
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
iiGetAvailableValuesForKeyLike(*key, *searchString, *isCollection, *values){
	*values = list();
	if(*isCollection){
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE 
			META_COLL_ATTR_NAME like '*key' AND
			META_COLL_ATTR_VALUE like '%*searchString%') {
			writeLine("stdout", *row.META_COLL_ATTR_VALUE);
			*values = cons(*row.META_COLL_ATTR_VALUE,*values);
			writeLine("serverLog", *row.META_COLL_ATTR_VALUE);
		}
	} else {
		foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE 
			META_DATA_ATTR_NAME like '*key' AND
			META_DATA_ATTR_VALUE like '%*searchString%') {
			*values = cons(*row.META_DATA_ATTR_VALUE,*values);
		}
	}
}
iiPrepareMetadataImport(*metadataxmlpath, *rodsZone, *xsdpath, *xslpath) {
	*xsdpath = "";
	*xslpath = "";
	*isfound = false;
	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	foreach(*row in
	       	SELECT USER_GROUP_NAME
	       	WHERE COLL_NAME = *metadataxml_coll
	          AND DATA_NAME = *metadataxml_basename
	          AND USER_GROUP_NAME like "research-%"
		  ) {
		if(!*isfound) {
			*groupName = *row.USER_GROUP_NAME;
			*isfound = true;
	 	} else {
			fail(-54000);
		}
	}
	if (!*isfound) {
		fail(-808000);
	}
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*xsdcoll = "/*rodsZone" ++ IIXSDCOLLECTION;
	*xsdname = "*category.xsd";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdcoll AND DATA_NAME = *xsdname) {
		*xsdpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	if (*xsdpath == "") {
		*xsdpath = "/*rodsZone" ++ IIXSDCOLLECTION ++ "/" ++ IIXSDDEFAULTNAME;
	}
	*xslcoll = "/*rodsZone" ++ IIXSDCOLLECTION;
	*xslname = "*category.xsl";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xslcoll AND DATA_NAME = *xslname) {
		*xslpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	if (*xslpath == "") {
		*xslpath = "/*rodsZone" ++ IIXSLCOLLECTION ++ "/" ++ IIXSLDEFAULTNAME;
	}
}
iiPrepareMetadataForm(*path, *result) {
	msiString2KeyValPair("", *kvp);
	iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager); 
	*kvp.groupName = *groupName;
	*kvp.userType = *userType;
	if (*isDatamanager) {
		*kvp.isDatamanager = "yes";
	} else {
		*kvp.isDatamanager = "no";
	}
	iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, true, *kvpList);
	*orgStatus = UNPROTECTED;
	foreach(*metadataKvp in *kvpList) {
		if (*metadataKvp.attrName == "status") {
			*orgStatus = *metadataKvp.attrValue;
			break;
		}
	}
	*kvp.folderStatus = *orgStatus;
	*lockFound = "no";
	foreach(*metadataKvp in *kvpList) {
		if (*metadataKvp.attrName like "lock_*") {
			*rootCollection = *metadataKvp.attrValue;
			if (*rootCollection == *path) {
				*lockFound = "here";
				break;
			} else {
				*descendants = triml(*rootCollection, *path);
				if (*descendants == *rootCollection) {
					*ancestors = triml(*path, *rootCollection);
					if (*ancestors == *path) {
						*lockFound = "outoftree";
					} else {
						*lockFound = "ancestor";
						break;
					}
				} else {
					*lockFound = "descendant";
					break;
				}
			}
		}
	}
	*kvp.lockFound = *lockFound;
	if (*lockFound != "no") {
		*kvp.lockRootCollection = *rootCollection;
	}
	*xmlname = IIMETADATAXMLNAME;	
	*xmlpath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *path AND DATA_NAME = *xmlname) {
	        *xmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	if (*xmlpath == "") {
		*kvp.hasMetadataXml = "false";
		*kvp.metadataXmlPath = *path ++ "/" ++ IIMETADATAXMLNAME;
	} else {
		*kvp.hasMetadataXml = "true";
		*kvp.metadataXmlPath = *xmlpath;
		iiDataObjectMetadataKvpList(*path, UUORGMETADATAPREFIX ++ "lock_", true, *metadataXmlLocks);
		uuKvpList2JSON(*metadataXmlLocks, *json_str, *size);
		*kvp.metadataXmlLocks = *json_str;	
	}	
	uuGroupGetCategory(*groupName, *category, *subcategory);
	*kvp.category = *category;
	*kvp.subcategory = *subcategory;
	*xsdcoll = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION;
	*xsdname = "*category.xsd";
	*xsdpath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *xsdcoll AND DATA_NAME = *xsdname) {
		*xsdpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	if (*xsdpath == "") {
		*xsdpath = "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/" ++ IIXSDDEFAULTNAME;
	}
	*kvp.xsdPath = *xsdpath;
	*formelementscoll = "/" ++ $rodsZoneClient ++ IIFORMELEMENTSCOLLECTION;
	*formelementsname = "*category.xml";
	*formelementspath = "";
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE COLL_NAME = *formelementscoll AND DATA_NAME = *formelementsname) {
		*formelementspath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
	}
	if (*formelementspath == "") {
		*kvp.formelementsPath = "/" ++ $rodsZoneClient ++ IIFORMELEMENTSCOLLECTION ++ "/" ++ IIFORMELEMENTSDEFAULTNAME;
	} else {
		*kvp.formelementsPath = *formelementspath;
	}
	uuChopPath(*path, *parent, *child);
	*kvp.parentHasMetadataXml = "false";
	foreach(*row in SELECT DATA_NAME, COLL_NAME WHERE COLL_NAME = *parent AND DATA_NAME = *xmlname) {
		*parentxmlpath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		*err = errormsg(msiXmlDocSchemaValidate(*parentxmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
		} else if (*err == 0) {
				*kvp.parentHasMetadataXml = "true";
				*kvp.parentMetadataXmlPath = *parentxmlpath;
		} else {
			writeLine("serverLog", "iiPrepareMetadataForm: *err");
			writeBytesBuf("serverLog", *status_buf);
		}
	}
	uuKvp2JSON(*kvp, *result);
}
iiRemoveAllMetadata(*path) {
	*metadataxmlpath =  *path ++ "/" ++ IIMETADATAXMLNAME;
	msiAddKeyValToMspStr("objPath", *metadataxmlpath, *options);
	msiAddKeyValToMspStr("forceFlag", "", *options);
	*err = errorcode(msiDataObjUnlink(*options, *status));
	writeLine("serverLog", "iiRemoveMetadata *path returned errorcode: *err");
}
iiRemoveAVUs(*coll, *prefix) {
	writeLine("serverLog", "iiRemoveAVUs: Remove all AVU's from *coll prefixed with *prefix");
	msiString2KeyValPair("", *kvp);
	*prefix = *prefix ++ "%";
	*duplicates = list();
	*prev = "";
	foreach(*row in SELECT order_asc(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		if (*attr == *prev) {
			writeLine("serverLog", "iiRemoveAVUs: Duplicate attribute " ++ *attr);
		       *duplicates = cons((*attr, *val), *duplicates);
		} else {	
			msiAddKeyVal(*kvp, *attr, *val);
			writeLine("serverLog", "iiRemoveAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
			*prev = *attr;
		}
	}
	msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	foreach(*pair in *duplicates) {
		(*attr, *val) = *pair;
		writeLine("serverLog", "iiRemoveUserAVUs: Duplicate key Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *attr, *val);
		msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	}
}
iiImportMetadataFromXML (*metadataxmlpath, *xslpath) {
	msiXsltApply(*xslpath, *metadataxmlpath, *buf);
	writeBytesBuf("serverLog", *buf);
	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	*err = errormsg(msiLoadMetadataFromXmlBuf(*metadataxml_coll, *buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiImportMetadataFromXML: *err - *msg ");
	} else {
		writeLine("serverLog", "iiImportMetadataFromXML: Succesfully loaded metadata from XML");
	}
}
iiCloneMetadataXml(*src, *dst) {
	msiDataObjCopy(*src, *dst, "", *status);
}
iiMetadataXmlModifiedPost(*xmlpath, *zone) {
	uuChopPath(*xmlpath, *parent, *basename);
	writeLine("serverLog", "iiMetadataXmlModifiedPost: *basename added to *parent. Import of metadata started");
	iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath);
	*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", *msg);
	} else if (*err == 0) {
		writeLine("serverLog", "XSD validation successful. Start indexing");
		iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
		iiImportMetadataFromXML(*xmlpath, *xslpath);
	} else {
		writeBytesBuf("serverLog", *status_buf);
	}
}
iiLogicalPathFromPhysicalPath(*physicalPath, *logicalPath, *zone) {
	*lst = split(*physicalPath, "/");
	uuListIndexOf(*lst, "home", *idx);
	if (*idx < 0) {
		writeLine("serverLog","iiLogicalPathFromPhysicalPath: Could not find home in *physicalPath. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		fail;
	}
	for( *el = 0; *el < *idx; *el = *el + 1) {
		*lst = tl(*lst);
	}
	*lst	= cons(*zone, *lst);
	uuJoin("/", *lst, *logicalPath);
	*logicalPath = "/" ++ *logicalPath;
	writeLine("serverLog", "iiLogicalPathFromPhysicalPath: *physicalPath => *logicalPath");
}
iiMetadataXmlRenamedPost(*src, *dst, *zone) {
	uuChopPath(*src, *src_parent, *src_basename);
	uuChopPath(*dst, *dst_parent, *dst_basename);
	if (*dst_basename != IIMETADATAXMLNAME && *src_parent == *dst_parent) {
		writeLine("serverLog", "pep_resource_rename_post: " ++ IIMETADATAXMLNAME ++ " was renamed to *dst_basename. *src_parent loses user metadata.");
		iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
	} else if (*src_parent != *dst_parent) {
		if (uuCollectionExists(*src_parent)) {
			iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
			writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent. Remove User Metadata from *src_parent.");
		} else {
			writeLine("serverLog", "iiMetadataXmlRenamedPost: " ++ IIMETADATAXMLNAME ++ " was moved to *dst_parent and *src_parent is gone.");
		}
	}
}
iiMetadataXmlUnregisteredPost(*logicalPath) {
	uuChopPath(*logicalPath, *parent, *basename);
	if (uuCollectionExists(*parent)) {
		writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename removed. Removing user metadata from *parent");
		iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
	} else {
		writeLine("serverLog", "iiMetadataXmlUnregisteredPost: *basename was removed, but *parent is also gone.");
	}			
}
iiRenameInvalidXML(*xmlpath, *xsdpath) {
		*invalid = false;
		*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
			*invalid = true;
		} else {
			msiBytesBufToStr(*status_buf, *status_str);
			*len = strlen(*status_str);
			if (*len == 0) {
				writeLine("serverLog", "XSD validation returned no output. This implies successful validation.");
			} else {
				writeBytesBuf("serverLog", *status_buf);
				*invalid = true;
			}
		}
		if (*invalid) {
			writeLine("serverLog", "Renaming corrupt or invalid $objPath");
			msiGetIcatTime(*timestamp, "unix");
			*iso8601 = uuiso8601(*timestamp);
			msiDataObjRename(*xmlpath, *xmlpath ++ "_invalid_" ++ *iso8601, 0, *status_rename);
		}
}
iiIsStatusTransitionLegal(*fromstatus, *tostatus) {
	*legal = false;
	foreach(*legaltransition in IIFOLDERTRANSITIONS) {
		(*legalfrom, *legalto) = *legaltransition;
		if (*legalfrom == *fromstatus && *legalto == *tostatus) {
			*legal = true;
			break;
		}
	}
	*legal;
}
iiGetLocks(*objPath, *locks, *locked) {
	*locked = false;
	*lockprefix = UUORGMETADATAPREFIX ++ "lock_";
	msiGetObjType(*objPath, *objType);
	msiString2KeyValPair("", *locks);
	if (*objType == '-d') {
		uuChopPath(*objPath, *collection, *dataName);
		foreach (*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE
					WHERE COLL_NAME = '*collection'
					  AND DATA_NAME = '*dataName'
					  AND META_DATA_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = triml(*row.META_DATA_ATTR_NAME, *lockprefix);
			*rootCollection= *row.META_DATA_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, *lockName, *valid);
			writeLine("serverLog", "iiGetLocks: *objPath -> *lockName=*rootCollection [valid=*valid]");
			if (*valid) {
				*locks."*lockName" = *rootCollection;
				*locked = true;
			}
		}
	} else {
		foreach (*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
					WHERE COLL_NAME = '*objPath'
					  AND META_COLL_ATTR_NAME like '*lockprefix%'
			) {
			*lockName = triml(*row.META_COLL_ATTR_NAME, *lockprefix);
			*rootCollection = *row.META_COLL_ATTR_VALUE;
			uuListContains(IIVALIDLOCKS, *lockName, *valid);
			writeLine("serverLog", "iiGetLocks: *objPath -> *lockName=*rootCollection [valid=*valid]");
			if (*valid) {
				*locks."*lockName" = *rootCollection;
				*locked = true;
			}
		}
	}
}
iiCanCollCreate(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown failure";
	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if (*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks."*lockName";
			if (strlen(*rootCollection) > strlen(*parent)) {
				*reason = "lock *lockName found on *parent, but Starting from *rootCollection" ;
				*allowed = true;
			} else {
				*reason = "lock *lockName found on *parent. Disallowing creating subcollection: *basename";
				*allowed = false;
				break;
			}
		}
	} else {
		*reason = "No locks found on *parent";
		*allowed = true;
	}
	writeLine("serverLog", "iiCanCollCreate: *path; allowed=*allowed; reason=*reason");
}
iiCanCollRename(*src, *dst, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "*src is has locks *locks";	
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks, *locked);
		if (*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent renaming subcollections."
				} else {
					*allowed = false;
					*reason = "*dstparent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No Locks found";
		}
	}
	writeLine("serverLog", "iiCanCollRename: *src -> *dst; allowed=*allowed; reason=*reason");
}
iiCanCollDelete(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error"; 	
	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "Locked with *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	writeLine("serverLog", "iiCanCollDelete: *path; allowed=*allowed; reason=*reason");
}
iiCanDataObjCreate(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks, *locked);
	if(*locked) {
		foreach(*lockName in *locks) {
			*rootCollection = *locks."*lockName";
			if (strlen(*rootCollection) > strlen(*parent)) {
				*allowed = true;
				*reason = "*parent has locked child *rootCollection, but this does not prevent creating new files."
			} else {
				*allowed = false;
				*reason = "*parent has lock(s) *locks";
				break;
			}
		}
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	writeLine("serverLog", "iiCanDataObjCreate: *path; allowed=*allowed; reason=*reason");
}
iiCanDataObjWrite(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "Locks found: *locks";
	} else  {
		uuChopPath(*path, *parent, *basename);
		iiGetLocks(*parent, *locks, *locked);
		if(*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*parent)) {
					*allowed = true;
					*reason = "*parent has locked child *rootCollection, but this does not prevent writing to files."
				} else {
					*allowed = false;
					*reason = "*parent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}
	writeLine("serverLog", "iiCanDataObjWrite: *path; allowed=*allowed; reason=*reason");
}
iiCanDataObjRename(*src, *dst, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks, *locked);
	if(*locked) {
		*allowed = false;
		*reason = "*src is locked with *locks";
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks, *locked);
		if(*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent writing to files."
				} else {
					*allowed = false;
					*reason = "*dstparent has lock(s) *locks";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}
	writeLine("serverLog", "iiCanDataObjRename: *src -> *dst; allowed=*allowed; reason=*reason");
}
iiCanDataObjDelete(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown Error";
	iiGetLocks(*path, *locks, *locked);
	if(*locked) {
		*reason = "Found lock(s) *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	writeLine("serverLog", "iiCanDataObjDelete: *path; allowed=*allowed; reason=*reason");
}
iiCanCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName, *allowed, *reason) {	
	*allowed = false;
	*reason = "Unknown error";
	if (*targetItemType == "-C") {	
		iiGetLocks(*targetItemName, *locks, *locked);
		if (*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*targetItemName)) {
					*allowed = true;
					*reason = "*rootCollection is locked, but does not affect metadata copy to *targetItemName";
				} else {
					*allowed = false;
				*reason = "*targetItemName is locked";	
				break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	} else if (*targetItemType == "-d") {
		   iiGetLocks(*targetItemName, *locks, *locked);
		if (*locked) {
			*reason = "*targetItemName has lock(s) *locks";
		} else {
			*allowed = true;
			*reason = "No locks found.";
		}
	} else {
		*allowed = true;
		*reason = "Restrictions only apply on Collections and DataObjects";
	}
	writeLine("serverLog", "iiCanCopyMetadata: *sourceItemName -> *targetItemName; allowed=*allowed; reason=*reason");
}
iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*itemName, *locks, *locked);
	if (*locked) {
		if (*itemType == "-C") {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (strlen(*rootCollection) > strlen(*parent)) {
					*allowed = true;
					*reason = "Lock *lockName found, but starting from *rootCollection";
				} else {
					*allowed = false;
					*reason = "Lock *LockName found on *rootCollection";
					break;
				}
			}
		} else {
			*reason = "Locks found. *locks";	
		}
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	writeLine("serverLog", "iiCanModifyUserMetadata: *itemName; allowed=*allowed; reason=*reason");
}
iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = true;
	*reason = "No reason to lock OrgMetatadata yet";
	writeLine("serverLog", "iiCanModifyOrgMetadata: *itemName; allowed=*allowed; reason=*reason");
}
iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (*attributeName != UUORGMETADATAPREFIX ++ "status") {
		failmsg(-1, "iiCanModifyFolderStatus: Called for attribute *attributeName instead of FolderStatus.");
	}
	if (*option == "rm") {
		*transitionFrom = *attributeValue;
		*transitionTo =  UNPROTECTED;
	}
	if (*option == "add") {
		*transitionFrom = "";
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = *attributeName) {
			*transitionFrom = *row.META_COLL_ATTR_VALUE;
		}
		*transitionTo = *attributeValue;	
		if (*transitionFrom == "") {
			*transitionFrom = UNPROTECTED;
		}
	}
	if (*option == "set") {
		*transitionTo = *attributeValue;
		*transitionFrom = UNPROTECTED;
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *path AND META_COLL_ATTR_NAME = *attributeName) {
			*transitionFrom = *row.META_COLL_ATTR_VALUE;
		}
	}
	if (!iiIsStatusTransitionLegal(*transitionFrom, *transitionTo)) {
		*reason = "Illegal status transition from *transitionFrom to *transitionTo";
	} else {
		*allowed = true;
		*reason = "Legal status transition. *transitionFrom -> *transitionTo";
		iiGetLocks(*path, *locks, *locked);
		if (*locked) {
			foreach(*lockName in *locks) {
				*rootCollection = *locks."*lockName";
				if (*rootCollection != *path) {
					*allowed = false;
					*reason = "Found lock(s) *lockName starting from *rootCollection";
					break;
				}
			}
		}
	}
	writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}
iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue, *allowed, *reason) {
	writeLine("serverLog", "iiCanModifyFolderStatus:*option, *path, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue");
	*allowed = false;
	*reason = "Unknown error";
	if (*newAttributeName == ""  || *newAttributeName == UUORGMETADATAPREFIX ++ "status") {
		*transitionFrom = *attributeValue;
		*transitionTo = triml(*newAttributeValue, "v:");
		if (!iiIsStatusTransitionLegal(*transitionFrom, *transitionTo)) {
			*reason = "Illegal status transition from *transitionFrom to *transitionTo";
		} else {
			*allowed = true;
			*reason = "Legal status transition. *transitionFrom -> *transitionTo";
			iiGetLocks(*path, *locks, *locked);
			if (*locked) {
				foreach(*lockName in *locks) {
					*rootCollection = *locks."*lockName";
					if (*rootCollection != *path) {
						*allowed = false;
						*reason = "Found lock(s) *lockName starting from *rootCollection";
						break;
					}
				}
			}
		}
	} else {
		*reason = "*attributeName should not be changed to *newAttributeName";
	}
	writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}
iiFolderStatus(*folder, *folderstatus) {
	*folderstatuskey = UUORGMETADATAPREFIX ++ "status";
	*folderstatus = UNPROTECTED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *folderstatuskey) {
		*folderstatus = *row.META_COLL_ATTR_VALUE;
	}
}
iiFolderTransition(*path, *currentStatus, *newStatus) {
	if (*currentStatus == UNPROTECTED && *newStatus == PROTECTED) {
		iiFolderLockChange(*path, "protect", true, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == PROTECTED && (*newStatus == UNPROTECTED || *newStatus == "")) {
		iiFolderLockChange(*path, "protect", false, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == UNPROTECTED && *newStatus == SUBMITTED) {
		iiFolderLockChange(*path, "protect", true, *status);
		if (*status != 0) {
			failmsg(-1110000, "Rollback needed");
		}
	} else if (*currentStatus == PROTECTED && *newStatus == SUBMITTED) {
		succeed;
	}
}
iiFolderProtect(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ PROTECTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");
}
iiFolderUnprotect(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ UNPROTECTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");	
}
iiFolderSubmit(*folder) {
	*status_str = UUORGMETADATAPREFIX ++ "status=" ++ SUBMITTED;
	msiString2KeyValPair(*status_str, *statuskvp);
	msiSetKeyValuePairsToObj(*statuskvp, *folder, "-C");
}
iiFolderLockChange(*rootCollection, *lockName, *lockIt, *status){
	*lock_str = UUORGMETADATAPREFIX ++ "lock_" ++ *lockName ++ "=" ++ *rootCollection;
	writeLine("ServerLog", "iiFolderLockChange: *lock_str");
	msiString2KeyValPair(*lock_str, *buffer)
	if (*lockIt) {
		writeLine("serverLog", "iiFolderLockChange: recursive locking of *rootCollection");
		*direction = "forward";
		uuTreeWalk(*direction, *rootCollection, "iiAddMetadataToItem", *buffer, *error);
		if (*error == 0) {
			uuChopPath(*rootCollection, *parent, *child);
			while(*parent != "/$rodsZoneClient/home") {
				uuChopPath(*parent, *coll, *child);
				iiAddMetadataToItem(*coll, *child, true, *buffer, *error); 
			 	*parent = *coll;
			}
		}
	} else {
		writeLine("serverLog", "iiFolderLockChange: recursive unlocking of *rootCollection");
		*direction="reverse";
		uuTreeWalk(*direction, *rootCollection, "iiRemoveMetadataFromItem", *buffer, *error);	
		if (*error == 0) {
			uuChopPath(*rootCollection, *parent, *child);
			while(*parent != "/$rodsZoneClient/home") {
				uuChopPath(*parent, *coll, *child);
				iiRemoveMetadataFromItem(*coll, *child, true, *buffer, *error); 
			 	*parent = *coll;
			}
		}
	}
	*status = *error;
}
iitypeabbreviation(*itemIsCollection) =  if *itemIsCollection then "-C" else "-d"
iiAddMetadataToItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiAddMetadataToItem: Setting *buffer on *objPath");
	*error = errorcode(msiAssociateKeyValuePairsToObj(*buffer, *objPath, *objType));
}
iiRemoveMetadataFromItem(*itemParent, *itemName, *itemIsCollection, *buffer, *error) {
	*objPath = "*itemParent/*itemName";
	*objType = iitypeabbreviation(*itemIsCollection);
	writeLine("serverLog", "iiRemoveMetadataKeyFromItem: Removing *buffer on *objPath");
	*error = errormsg(msiRemoveKeyValuePairsFromObj(*buffer, *objPath, *objType), *msg);
	if (*error < 0) {
		writeLine("serverLog", "iiRemoveMetadataFromItem: removing *buffer from *objPath failed with errorcode: *error");
		writeLine("serverLog", *msg);
		if (*error == -819000) {
			writeLine("serverLog", "iiRemoveMetadaFromItem: -819000 detected. Keep on trucking");
			*error = 0;
		}
	}
}
acPostProcForPut {
	on ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanDataObjCreate($objPath, *allowed, *reason);
		if (!*allowed) {
			msiDataObjUnlink("objPath=$objPath++++forceFlag=", *status);	
		}
	}
	on ($objPath like regex "/[^/]+/" ++ IIXSDCOLLECTION ++ "/.*\.xsd") {
		*xsdpath =  "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/schema-for-xsd.xsd";		
		iiRenameInvalidXML($objPath, *xsdpath);
	}
	on ($objPath like regex "/[^/]+/" ++ IIFORMELEMENTSCOLLECTION ++ "/.*\.xml") {
		*xsdpath =  "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/schema-for-formelements.xsd";		
		iiRenameInvalidXML($objPath, *xsdpath);
	}
}
acPreprocForRmColl {
	on($collName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanCollDelete($collName, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
acDataDeletePolicy {
	on($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanDataObjDelete($objPath, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiDeleteDisallowed;
		}
	}
}
acPreprocForCollCreate {
	on($collName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		writeLine("serverLog", "acPreprocForCollCreate: $collName");
		iiCanCollCreate($collName, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
acPreProcForObjRename(*src, *dst) {
	on($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		msiGetObjType($objPath, *objType);
		if (*objType == "-c") {
			iiCanCollRename(*src, *dst, *allowed, *reason);
			if(!*allowed) {
				cut;
				msiOprDisallowed;
			}	
		} else {
			iiCanDataObjRename(*src, *dst, *allowed, *reason);
			if(!*allowed) {
				cut;
				msiOprDisallowed;
			}
		}
	}
}
acPreprocForDataObjOpen {
	on ($writeFlag == "1" && $objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		writeLine("serverLog", "acPreprocForDataObjOpen: $objPath");
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanDataObjWrite($objPath, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) {
	on ((*SourceItemType == "-C" || *SourceItemType == "-d") && (*SourceItemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*" || *TargetItemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*")) {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanCopyMetadata(*Option, *SourceItemType, *TargetItemType, *SourceItemName, *TargetItemName, *allowed, *reason);
		if (!allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
	on (*attributeName like UUUSERMETADATAPREFIX ++ "*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
	on (*attributeName like UUORGMETADATAPREFIX ++ "*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		if (*attributeName == UUORGMETADATAPREFIX ++ "status") {
			iiCanModifyFolderStatus(*option, *itemName, *attributeName, *attributeValue, *allowed, *reason);
			if (*allowed) {
				iiFolderStatus(*itemName, *currentStatus);
				*err = errorcode(iiFolderTransition(*itemName, *currentStatus, *attributeValue));
				if (*err < 0) {
					*allowed = false;
				}
			}
		} else {
			*allowed = true;
		}
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit,  *newAttributeName, *newAttributeValue, *newAttributeUnit) {
	on (*attributeName like UUUSERMETADATAPREFIX ++ "*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) ;
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
	on (*attributeName like UUORGMETADATAPREFIX ++ "*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}
		if (*attributeName == UUORGMETADATAPREFIX ++ "status") {
			iiCanModifyFolderStatus(*option, *itemName, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue, *allowed, *reason); 
			if (*allowed) {
				iiFolderStatus(*itemName, *currentStatus);
				*err = errorcode(iiFolderTransition(*itemName, *currentStatus,*attributeValue));
				if (*err < 0) {
					*allowed = false;
				}
			}
		} else {
			*allowed = true;
		}
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}
uuResourceModifiedPostResearch(*pluginInstanceName, *KVPairs) {
	if (*KVPairs.logical_path like regex "^/" ++ *KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$") {
		writeLine("serverLog", "uuResourceModifiedPostResearch:\n KVPairs = *KVPairs\npluginInstanceName = *pluginInstanceName");
		iiMetadataXmlModifiedPost(*KVPairs.logical_path, *KVPairs.client_user_zone);
	}
}
uuResourceRenamePostResearch(*pluginInstanceName, *KVPairs) {
	if (*KVPairs.physical_path like regex ".\*/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$") {
		writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		*zone =  *KVPairs.client_user_zone;
		*dst = *KVPairs.logical_path;
		iiLogicalPathFromPhysicalPath(*KVPairs.physical_path, *src, *zone);
		iiMetadataXmlRenamedPost(*src, *dst, *zone);
	}
}
uuResourceUnregisteredPostResearch(*pluginInstanceName, *KVPairs) {
	if (*KVPairs.logical_path like regex "^/" ++ *KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$") {
		writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		iiMetadataXmlUnregisteredPost(*KVPairs.logical_path);
		}
}
orderclause(*column, *orderby, *ascdesc) = if *column == *orderby then orderdirection(*ascdesc) else ""
orderdirection(*ascdesc) = if *ascdesc == "desc" then "ORDER_DESC" else "ORDER_ASC"
iscollection(*collectionOrDataObject) = if *collectionOrDataObject == "Collection" then true else false
iiBrowse(*path, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection){
		*fields = list("COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path));
	} else {
		*fields = list("DATA_ID", "DATA_NAME", "MIN(DATA_CREATE_TIME)", "MAX(DATA_MODIFY_TIME)");
		*conditions =  list(uucondition("COLL_NAME", "=", *path));
	}
	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
	*kvpList = list()
	if (*iscollection) {
		foreach(*row in tl(*rowList)) {
			msiString2KeyValPair("", *kvp);
			*name =	*row.COLL_NAME;
			*kvp."path" = *name;
			*kvp.basename = triml(*name, *path ++ "/");
			*coll_id = *row.COLL_ID;
			*kvp.id = *coll_id;
			*kvp."irods_type" = "Collection";
			*kvp."create_time" = *row.COLL_CREATE_TIME;
			*kvp."modify_time" = *row.COLL_MODIFY_TIME;
			uuCollectionMetadataKvp(*coll_id, UUORGMETADATAPREFIX, *kvp);
			*kvpList = cons(*kvp, *kvpList);
		}
	} else {
		foreach(*row in tl(*rowList)) {
			msiString2KeyValPair("", *kvp);
			*name = *row.DATA_NAME;
			*kvp.basename = *name;
			*kvp."path" = *path ++ "/" ++ *name;
			*data_id = *row.DATA_ID;
			*kvp.id = *data_id;
			*kvp."create_time" = *row.DATA_CREATE_TIME;
			*kvp."modify_time" = *row.DATA_MODIFY_TIME;
			*kvp."irods_type" = "DataObject";
			uuObjectMetadataKvp(*data_id, UUORGMETADATAPREFIX, *kvp);
			*kvpList = cons(*kvp, *kvpList);
		}
	}
	*kvpList = cons(hd(*rowList), *kvpList);
	uuKvpList2JSON(*kvpList, *result, *size);
}
iiCollectionDetails(*path, *result) {
	if (!uuCollectionExists(*path)) {
		fail(-317000);
	}
	msiString2KeyValPair("path=*path", *kvp);
	foreach(*row in SELECT COLL_ID, COLL_NAME, COLL_PARENT_NAME, COLL_MODIFY_TIME, COLL_CREATE_TIME WHERE COLL_NAME = *path) {
		*parent = *row.COLL_PARENT_NAME;
		*kvp.parent = *parent;
		*kvp.basename = triml(*path, *parent ++ "/");
		*coll_id = *row.COLL_ID;
		*kvp.id = *coll_id;
		*kvp."irods_type" = "Collection";
		*kvp."coll_create_time" = *row.COLL_CREATE_TIME;
		*kvp."coll_modify_time" = *row.COLL_MODIFY_TIME;
	}
	iiFileCount(*path, *totalSize, *dircount, *filecount, *modified);
	*kvp.dircount = *dircount;
	*kvp.totalSize = *totalSize;
	*kvp.filecount = *filecount;
	*kvp.content_modify_time = *modified;
	iiCollectionMetadataKvpList(*path, UUORGMETADATAPREFIX, true, *kvpList);
	uuKvpList2JSON(*kvpList, *orgMetadata_json, *size);
	*kvp.orgMetadata = *orgMetadata_json;
	if (*path like "/$rodsZoneClient/home/" ++ IIGROUPPREFIX ++ "*") {
		*kvp.userMetadata = "true";
		iiCollectionGroupNameAndUserType(*path, *groupName, *userType, *isDatamanager); 
		*kvp.groupName = *groupName;
		*kvp.userType = *userType;
		if (*isDatamanager) {
			*kvp.isDatamanager = "yes";
		} else {
			*kvp.isDatamanager = "no";
		}
		*orgStatus = UNPROTECTED;
		foreach(*metadataKvp in *kvpList) {
			if (*metadataKvp.attrName == "status") {
				*orgStatus = *metadataKvp.attrValue;
				break;
			}
		}
		*kvp.folderStatus = *orgStatus;
		*lockFound = "no";
		foreach(*metadataKvp in *kvpList) {
			if (*metadataKvp.attrName like "lock_*") {
				*rootCollection = *metadataKvp.attrValue;
				*kvp.lockRootCollection = *rootCollection;
				if (*rootCollection == *path) {
					*lockFound = "here";
				} else {
					*children = triml(*rootCollection, *path);
					if (*children == *rootCollection) {
						*ancestors = triml(*path, *rootCollection);
						if (*ancestors == *path) {
							*lockFound = "outoftree";
						} else {
							*lockFound = "ancestor";
						}
					} else {
						*lockFound = "descendant";
					}
				}
			}
		}
		*kvp.lockFound = *lockFound;
	}
	uuKvp2JSON(*kvp, *result);
}
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
iiSearchByName(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection) {
		*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(uumakelikecollcondition("COLL_NAME", *searchstring));
		*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);
		uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
		iiKvpCollectionTemplate(*rowList, *kvpList);
	} else {
		*fields = list("COLL_NAME", "DATA_ID", "DATA_NAME", "MIN(DATA_CREATE_TIME)", "MAX(DATA_MODIFY_TIME)");
		*conditions = list(uumakelikecondition("DATA_NAME", *searchstring));
		*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);
		uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
		iiKvpDataObjectsTemplate(*rowList, *kvpList);
	}
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}
iiSearchByMetadata(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	*iscollection = iscollection(*collectionOrDataObject);
	*likeprefix = UUUSERMETADATAPREFIX ++ "%";
	if (*iscollection) {
		*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(uumakelikecondition("META_COLL_ATTR_VALUE", *searchstring),
				   uumakestartswithcondition("META_COLL_ATTR_NAME", UUUSERMETADATAPREFIX),
				   uumakestartswithcondition("COLL_PARENT_NAME", *startpath));
		uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
		iiKvpCollectionTemplate(*rowList, *kvpList);	
		foreach(*kvp in tl(*kvpList)) {
			*coll_id = *kvp.id;
			*matches = "[]";
			*msize = 0;
			foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_ID = *coll_id AND META_COLL_ATTR_NAME like *likeprefix AND META_COLL_ATTR_VALUE like "%*searchstring%") {
				msiString2KeyValPair("", *match);
				*name_lst = split(*row.META_COLL_ATTR_NAME, "_");
				uuJoin(" ", tl(tl(*name_lst)), *name);
				*val = *row.META_COLL_ATTR_VALUE;
				msiAddKeyVal(*match, *name, *val);
				*match_json = "";
				msi_json_objops(*match_json, *match, "set");
				msi_json_arrayops(*matches, *match_json, "add", *msize);
			}
			*kvp.matches = *matches;
		}	
	} else {
		*fields = list("COLL_NAME", "DATA_ID", "DATA_NAME", "MIN(DATA_CREATE_TIME)", "MAX(DATA_MODIFY_TIME)");
		*conditions = list(uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring),
				   uumakestartswithcondition("META_COLL_ATTR_NAME", UUUSERMETADATAPREFIX),
				   uumakestartswithcondition("COLL_NAME", *startpath));
		uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
		iiKvpDataObjectsTemplate(*rowList, *kvpList);
		foreach(*kvp in tl(*kvpList)) {
			*data_id = *kvp.id;
			*matches = "[]";
			*msize = 0;
			foreach(*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *data_id AND META_DATA_ATTR_NAME like *likeprefix AND META_DATA_ATTR_VALUE like "%*searchstring%") {
				msiString2KeyValPair("", *match);
				*name = triml(*row.META_DATA_ATTR_NAME, UUUSERMETADATAPREFIX);
				*val = *row.META_DATA_ATTR_VALUE;
				msiAddKeyVal(*match, *name, *val);
				*match_json = "";
				msi_json_objops(*match_json, *match, "set");
				msi_json_arrayops(*matches, *match_json, "add", *msize);
			}
			*kvp.matches = *matches;
		}	
	}
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}
iiSearchByOrgMetadata(*startpath, *searchstring, *attrname, *orderby, *ascdesc, *limit, *offset, *result) {
	*attr = UUORGMETADATAPREFIX ++ *attrname;
	*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
	*conditions = list(uumakelikecondition("META_COLL_ATTR_VALUE", *searchstring));
	*conditions = cons(uucondition("META_COLL_ATTR_NAME", "=", *attr), *conditions);
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);
	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *rowList);
	iiKvpCollectionTemplate(*rowList, *kvpList);
	uuKvpList2JSON(*kvpList, *result, *size);
}
iiKvpCollectionTemplate(*rowList, *kvpList) {
	*kvpList = list();
	foreach(*row in tl(*rowList)) {
		msiString2KeyValPair("", *kvp);
		*name =	*row.COLL_NAME;
		*kvp."path" = *name;
		*parent = *row.COLL_PARENT_NAME;
		*kvp.parent = *parent;
		*basename = triml(*name, *parent ++ "/");
		*kvp.basename = *basename;
		*coll_id = *row.COLL_ID;
		*kvp.id = *coll_id;
		*kvp."irods_type" = "Collection";
		*kvp."create_time" = *row.COLL_CREATE_TIME;
		*kvp."modify_time" = *row.COLL_MODIFY_TIME;
		uuCollectionMetadataKvp(*coll_id, UUORGMETADATAPREFIX, *kvp);
		*kvpList = cons(*kvp, *kvpList);
	}
	*kvpList = cons(hd(*rowList), *kvpList);
}
iiKvpDataObjectsTemplate(*rowList, *kvpList) {
	*kvpList = list();
	foreach(*row in tl(*rowList)) {
		msiString2KeyValPair("", *kvp);
		*name = *row.DATA_NAME;
		*kvp.basename = *name;
		*parent = *row.COLL_NAME;
		*kvp.parent = *parent;
		*kvp."path" = *parent ++ "/" ++ *name;
		*data_id = *row.DATA_ID;
		*kvp.id = *data_id;
		*kvp."create_time" = *row.DATA_CREATE_TIME;
		*kvp."modify_time" = *row.DATA_MODIFY_TIME;
		*kvp."irods_type" = "DataObject";
		uuObjectMetadataKvp(*data_id, UUORGMETADATAPREFIX, *kvp);
		*kvpList = cons(*kvp, *kvpList);
	}
	*kvpList = cons(hd(*rowList), *kvpList);
}
uuResourceModifiedPostRevision(*pluginInstanceName, *KVPairs) {
	if (*KVPairs.logical_path like "/" ++ *KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "*") {
		writeLine("serverLog", "uuResourceModifiedPostRevision:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		*path = *KVPairs.logical_path;
		uuChopPath(*path, *parent, *basename);
		if (*basename like "._*") {
			writeLine("serverLog", "uuResourceModifiedPostRevision: Ignore *basename for revision store. This is littering by Mac OS");
		} else {
			iiRevisionCreateAsynchronously(*path);
		}
	}
}
iiRevisionCreateAsynchronously(*path) {
	remote("localhost", "") {
		delay("<PLUSET>1s</PLUSET>") {
			iiRevisionCreate(*path, *id);
			writeLine("serverLog", "iiRevisionCreate: Revision created for *path ID=*id");
		}
	}
}
iiRevisionCreate(*path, *id) {
	*id = "";
	uuChopPath(*path, *parent, *basename);
	*objectId = 0;
	*found = false;
	foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID
	       		WHERE DATA_NAME = *basename AND COLL_NAME = *parent AND DATA_REPL_NUM = "0") {
		if (!*found) {
			*found = true;
			*dataId = *row.DATA_ID;
			*modifyTime = *row.DATA_MODIFY_TIME;
			*dataSize = *row.DATA_SIZE;
			*collId = *row.COLL_ID;
			*dataOwner = *row.DATA_OWNER_NAME;
		}
	}
	if (!*found) {
		writeLine("serverLog", "iiRevisionCreate: DataObject was not found or path was collection");
		succeed;
	}
	if (int(*dataSize)>500048576) {
		writeLine("serverLog", "iiRevisionCreate: Files larger than 500MiB cannot store revisions");
		succeed;
	}	
	foreach(*row in SELECT USER_NAME, USER_ZONE WHERE DATA_ID = *dataId AND USER_TYPE = "rodsgroup" AND DATA_ACCESS_NAME = "own") {
	       *groupName = *row.USER_NAME;
		*userZone = *row.USER_ZONE;
	}
	*revisionStore = "/*userZone" ++ UUREVISIONCOLLECTION ++ "/*groupName";
	foreach(*row in SELECT COUNT(COLL_ID) WHERE COLL_NAME = *revisionStore) {
	       	*revisionStoreExists = bool(int(*row.COLL_ID));
       	}
	if (*revisionStoreExists) {
		msiGetIcatTime(*timestamp, "icat");
		*iso8601 = timestrf(datetime(int(*timestamp)), "%Y%m%dT%H%M%S%z");
		*revFileName = *basename ++ "_" ++ *iso8601 ++ *dataOwner;
		*revColl = *revisionStore ++ "/" ++ *collId;
		*revPath = *revColl ++ "/" ++ *revFileName;
		*err = errorcode(msiDataObjCopy(*path, *revPath, "verifyChksum=", *msistatus));
		if (*err < 0) {
			if (*err == -312000) {
				writeLine("serverLog", "iiRevisionCreate: *revPath already exists. This means that *basename was changed multiple times within the same second.");
			} else if (*err == -814000) {
				writeLine("serverLog", "iiRevisionCreate: Could not access or create *revColl. Please check permissions");
			} else {
				failmsg(*err, "iiRevisionCreate failed");
			}
		} else {
			foreach(*row in SELECT DATA_ID WHERE DATA_NAME = *revFileName AND COLL_NAME = *revColl) {
				*id = *row.DATA_ID;
			}
			msiString2KeyValPair("", *revkv);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_path", *path);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_name", *parent);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_name", *basename);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_owner_name", *dataOwner);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_id", *dataId);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_id", *collId);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
			msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_group_name", *groupName);
			msiAssociateKeyValuePairsToObj(*revkv, *revPath, "-d");
		}
	} else {
		writeLine("serverLog", "iiRevisionCreate: *revisionStore does not exists or is inaccessible for current client.");
	}
}
iiRevisionRemove(*revision_id) {
	*isfound = false;
	*revisionStore =  "/$rodsZoneClient" ++ UUREVISIONCOLLECTION;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revision_id" AND COLL_NAME like "*revisionStore/%") {
		if (!*isfound) {
			*isfound = true;
			*objPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		} else {
			writeLine("serverLog", "iiRevisionRemove: *revision_id returned multiple results");
		}
	}
	if (*isfound) {
		*args = "";
		msiAddKeyValToMspStr("objPath", *objPath, *args);
		msiAddKeyValToMspStr("forceFlag", "", *args);
		msiDataObjUnlink(*args, *status);
		writeLine("serverLog", "iiRevisionRemove('*revision_id'): Removed *objPath from revision store");
	} else {
		writeLine("serverLog", "iiRevisionRemove: Revision_id not found or permission denied.");
	}
}
iiRevisionRestore(*revisionId, *target, *overwrite, *status, *statusInfo) {
        *status = "Unknown error";
        *isfound = false;
        *executeRestoration = false;
	*statusInfo = '';
        foreach(*rev in SELECT DATA_NAME, COLL_NAME WHERE DATA_ID = *revisionId) {
                if (!*isfound) {
                        *isfound = true;
                        *revName = *rev.DATA_NAME; # revision name is suffixed with a timestamp for uniqueness
                        *revCollName = *rev.COLL_NAME;
                        *src = *revCollName ++ "/" ++ *revName;
                        writeLine("serverLog", "Source is: *src");
                }
        }
        if (!*isfound) {
                writeLine("serverLog", "uuRevisionRestore: Could not find revision *revisionId");
                *status = "RevisionNotFound";
                succeed;
        }
        msiString2KeyValPair("", *kvp);
        uuObjectMetadataKvp(*revisionId, UUORGMETADATAPREFIX, *kvp);
        if (!uuCollectionExists(*target)) {
                writeLine("serverLog", "uuRevisionRestore: Cannot find target collection *target");
                *status = "TargetPathDoesNotExist";
                succeed;
        }
        if (*overwrite == "restore_no_overwrite") {
                *existsTargetFile = false;
                msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);
                foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = *target AND DATA_NAME = *oriDataName ) {
                        *existsTargetFile = true;
                        break;
                }
                if(*existsTargetFile) {
                        writeLine("serverLog", "File exists already");
                        *status = "FileExists";
                        succeed;
                }
                else { ## Revision can be restored directly - no user interference required
                        msiAddKeyValToMspStr("forceFlag", "", *options);
                        *dst = *target ++ "/" ++ *oriDataName;
                        *executeRestoration = true;
                }
        }
        else {
                if (*overwrite == "restore_overwrite") {
                        msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);
                        msiAddKeyValToMspStr("forceFlag", "", *options);
                        *dst = *target ++ "/" ++ *oriDataName;
                        *executeRestoration = true;
                } else if (*overwrite == "restore_next_to") {
                        *dst = *target ++ "/" ++ *revName;
                        *executeRestoration = true;
                }
                else {
                        *statusInfo = "Illegal overwrite flag *overwrite";
			writeLine("serverLog", "uuRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
			succeed;
                }
        }
        if (*executeRestoration) {
                msiAddKeyValToMspStr("verifyChksum", "", *options);
                writeLine("serverLog", "uuRevisionRestore: *src => *dst [*options]");
                *err = errormsg(msiDataObjCopy("*src", "*dst", *options, *msistatus), *errmsg);
                if (*err < 0) {
			if (*err==-818000) {
				*status = "PermissionDenied";
				succeed;
			}                        
			*statusInfo = "Restoration failed with error *err: *errmsg";
                        writeLine("serverLog", "uuRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
                } else {
                        *status = "Success";
                }
        }
}
iiRevisionLast(*originalPath, *isfound, *revision) {
	msiString2KeyValPair("", *revision);
	*isfound = false;
	foreach(*row in SELECT DATA_ID, DATA_CHECKSUM, order_desc(DATA_CREATE_TIME) WHERE META_DATA_ATTR_NAME = 'org_original_path' AND META_DATA_ATTR_VALUE = *originalPath) {
		if (!*isfound) {
			*isfound = true;
			*id = *row.DATA_ID;
			*revision.id = *id;
			*revision.checksum = *row.DATA_CHECKSUM;
			*revision.timestamp = *row.DATA_CREATE_TIME;
			foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
				*name = *meta.META_DATA_ATTR_NAME;
				*val = *meta.META_DATA_ATTR_VALUE;
				msiAddKeyVal(*revision, *name, *val);
			}
		}
	}
}
iiRevisionList(*path, *result) {
	*revisions = list();
	uuChopPath(*path, *coll_name, *data_name);
	*isFound = false;
	foreach(*row in SELECT DATA_ID, COLL_NAME, order_desc(DATA_NAME) 
		        WHERE META_DATA_ATTR_NAME = 'org_original_path' AND META_DATA_ATTR_VALUE = *path) {
		msiString2KeyValPair("", *kvp); # only way as far as I know to initialize a new key-value-pair object each iteration.
		*isFound = true;
		*id = *row.DATA_ID;
		*kvp.id = *id;
		*kvp.revisionPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			msiAddKeyVal(*kvp, *name, *val);	
		}
		*revisions = cons(*kvp, *revisions);
	}
	uuKvpList2JSON(*revisions, *result, *size);	
}
iiRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("META_DATA_ATTR_VALUE", "COUNT(DATA_ID)", "DATA_NAME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"),
			   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);
	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*res.originalPath = *kvp.META_DATA_ATTR_VALUE;
		*res.numberOfRevisions = *kvp.DATA_ID;
		*result_lst = cons(*res, *result_lst);
	}
	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}
iiRevisionSearchByOriginalFilename(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*originalDataNameKey = UUORGMETADATAPREFIX ++ "original_data_name";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", *originalDataNameKey),
        		   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));	
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);
	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*originalDataName = *kvp.META_DATA_ATTR_VALUE;
		*res.originalDataName = *originalDataName;
		*revisionColl = *kvp.COLL_NAME;
		*originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
		*revCount = 0;
		*isFound = false;
		foreach(*row in SELECT DATA_ID WHERE COLL_NAME = *revisionColl AND META_DATA_ATTR_NAME = *originalDataNameKey AND META_DATA_ATTR_VALUE = *originalDataName) {
			*revId = *row.DATA_ID;
			*revCount = *revCount + 1;
			uuObjectMetadataKvp(*revId, UUORGMETADATAPREFIX ++ "original", *mdkvp);
			msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_modify_time", *revModifyTime);
			if (!*isFound) {
				*isFound = true;
				msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_path", *originalPath);
				msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_coll_name", *originalCollName);
				*latestRevModifiedTime = int(*revModifyTime);
				*oldestRevModifiedTime = int(*revModifyTime);
			} else {
				*latestRevModifiedTime = max(*latestRevModifiedTime, int(*revModifyTime));
				*oldestRevModifiedTime = min(*oldestRevModifiedTime, int(*revModifyTime));
			}
		}
		*res.numberOfRevisions = str(*revCount);
		*res.originalPath = *originalPath;
		*res.originalCollName = *originalCollName;
		*res.latestRevisionModifiedTime = str(*latestRevModifiedTime);
		*res.oldestRevisionModifiedTime = str(*oldestRevModifiedTime);
		*res.collectionExists = 'false';  
		if ( uuCollectionExists(*originalCollName)) {
			*res.collectionExists = 'true'
		}					
		*result_lst = cons(*res, *result_lst);
	}
	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}
iiRevisionSearchByOriginalId(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME", "DATA_CHECKSUM", "DATA_SIZE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_id"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchid), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);
	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	foreach(*kvp in tl(*kvpList)) {
		*id = *kvp.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *kvp);
	}
	*kvpList = cons(hd(*kvpList), uuListReverse(tl(*kvpList)));
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}
