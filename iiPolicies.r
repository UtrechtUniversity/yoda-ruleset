# This policy is fired before a collection is deleted.
# The policy prohibits deleting the collection if the collection
# is locked
acPreprocForRmColl {
	   uuIiObjectActionAllowed($collName, *collAllows);
	   uuIiObjectActionAllowed($collParentName, *parentAllows);
	   if(!(*collAllows && *parentAllows)) {
			 writeLine("serverLog", "Disallowing deleting $collName");
			 cut;
			 msiDeleteDisallowed();
	   }
}

# This policy is fired before a data object is deleted
# The policy prohibits deleting the data object if the data object
# is locked. The parent collection is not checked
acDataDeletePolicy {
	   uuIiObjectActionAllowed($objPath, *allow);
	   if(!*allow) {
			 writeLine("serverLog", "Deleting $objPath not allowed");
			 cut;
			 msiDeleteDisallowed();
	   }
}

# This policy is fired before a collection is created
# The policy prohibits creating a new collection if the
# parent collection is locked
acPreprocForCollCreate {
	   uuIiObjectActionAllowed($collParentName, *allowed);
	   if(!*allowed) {
			 writeLine("serverLog", "Disallowing creating $collName collection");
			 cut;
			 msiOprDisallowed;
	   }
}

# This policy is fired after a collection is created.
# The policy checks if the new collection is on the datapackage level, 
# i.e. if it should be initialized with the version number 0
#acPostProcForCollCreate {
#	   writeLine("serverLog", "Jan's policy is getriggerd");
#	   uuIiGetIntakePrefix(*intakePrefix);
#	   *pathStart = "/"++$rodsZoneClient++"/home/"++*intakePrefix;
#	   if($collName like "*pathStart*") {
#			 uuIiIntakeLevel(*level);
#			 uuChop($collName, *head, *tail, *pathStart, true);
#			 *segments = split(*tail, "/");
#			 if(size(*segments) == *level) {
#				    uuIiVersionKey(*versionKey, *dependsKey);
#				    *alreadyHasVersion = false;
#				    foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE
#						  COLL_NAME = "$collName" AND 
#						  META_COLL_ATTR_NAME = *versionKey) {
#						  *alreadyHasVersion = true;
#						  break;
#				    }
#				    writeLine("serverLog", "Already has version is *alreadyHasVersion");
#				    if(!*alreadyHasVersion) {
#						  writeLine("serverLog", "New directory on the versioning level (typically Dataset or Datapackage)");
#						  msiAddKeyVal(*kv, *versionKey, str(1));
#						  *err = errorcode(msiSetKeyValuePairsToObj(*kv, $collName, "-C"));
#						  if(*err != 0) {
#								writeLine("serverLog", "Could not set initial version for $collName. Error code *err");
#						  }
#				    }
#			 }
#	   }
#}

# This policy is fired before a data object is renamed or moved
# The policy disallows renaming or moving the data object, if the
# object is locked, or if the collection that will be the new parent
# collection of the data object after the rename is locked
acPreProcForObjRename(*source, *destination) {
	   uuChopPath(*source, *sourceParent, *sourceBase);
	   uuChopPath(*destination, *destParent, *destBase);
	   uuIiObjectActionAllowed(*source, *sourceAllows);
	   uuIiObjectActionAllowed(*sourceParent, *sourceParentAllows);
	   uuIiObjectActionAllowed(*destParent, *destAllows);
	   if(!(*sourceAllows && *sourceParentAllows && *destAllows)) {
			 writeLine("serverLog", "Disallowing moving *source to *destination");
			 cut;
			 msiOprDisallowed;
	   }
}

# This policy is fired before a data object is opened.
# The policy does not prohibit opening data objects for reading,
# but if the data object is locked, opening for writing is 
# disallowed. Many editors open a file for reading while editing and
# store the file locally. Only when saving the changes, the file is
# opened for writing. IF the file is locked, this means changes can be
# created in the file, but they cannot be saved.
acPreprocForDataObjOpen {
	   ON ($writeFlag == "1") {
			 uuIiObjectActionAllowed($objPath, *objAllows);
			 if(!*objAllows) {
				    writeLine("serverLog", "Disallowing opening $objPath for writing");
				    cut;
				    msiOprDisallowed;
			 }
	   }
}

# This policy fires when a new data object is created
# The policy prohibits creating a new data object if the
# parent collection is locked
# The policy also sets the default rescource to the resource
# it would choose either way, because the policy is required
# to set a resource

#DOES NOT WORK
#acSetRescSchemeForCreate {
#        uuChopPath($objPath, *parent, *base);
#        uuIiObjectActionAllowed(*parent, *allowed);
#        if(!*allowed) {
#                writeLine("serverLog", "Creating data object $objPath not allowed");
#                cut;
#                msiOprDisallowed;
#        }
#        writeLine("serverLog", "Created resource. ObjPath = *objPath");
#        fail;
#        #msiSetDefaultResc("$destRescName", "null");
#}

# This policy is fired if the AVU meta data (AVU metadata is the non-system metadata)
# is modified in any way except for copying. The modification of meta data is prohibited
# if the object the meta data is modified on is locked
#acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) {
#	   uuIiObjectActionAllowed(*ItemName, *allowed);
#	   uuIiGetMetadataPrefix(*prfx);
#	   *startAllowed = *AName not like "*prfx\*";
#	   uuIiVersionKey(*versionKey, *dependsKey);
#	   uuIiIsAdminUser(*isAdminUser);
#	   if(!(*allowed || *startAllowed) || (
#			 !*isAdminUser && (
#				    (*AName == *versionKey && *AValue != "1") || 
#				    *AName == *dependsKey || 
#				    *AName == "dataset_snapshot_createdAtBy"
#			 )
#	   )) {
#			 writeLine("serverLog", "Metadata *AName = *AValue cannot be added to *ItemName");
#			 cut;
#			 msiOprDisallowed;
#	   }
#}

# This policy is fired if AVU meta data is copied from one object to another.
# Copying of metadata is prohibited by this policy if the target object is locked
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) {
	   uuIiObjectActionAllowed(*TargetItemName, *allowed);
	   if(!*allowed) {
			 writeLine("serverLog", "Metadata could not be copied from *SourceItemName to *TargetItemName because the latter is locked");
			 cut;
			 msiOprDisallowed;
	   }
}

# uuIiObjectActionAllowed 	Checks if any action on the target object is allowed
# 							i.e. if no lock exist. If the current user is the admin
# 							user, everything is allowed by default
# \param[in] objPath 		The full path to the object that is to be checked
# \param[out] allowed 		Bool indicating wether actions are allowed on this object
# 							at this time by the current user
#
uuIiObjectActionAllowed(*objPath, *allowed) {
	   *allowed = true;
	   msiGetObjType(*objPath, *type);
	   *isCollection = false;
	   if (*type == "-c") {
			 *isCollection = true;
	   }
	   iiObjectIsSnapshotLocked(*objPath, *isCollection, *snaplocked, *frozen);
	   if(*snaplocked || *frozen) {
			 uuIiIsAdminUser(*isAdminUser);
			 if(!*isAdminUser) {
				    *allowed = false;
			 }
	   }
}

# \brief uuIiIsAdminUser Check if current user is of type rodsadmin
# \param[out] isAdminUser	 true if user is rodsadmin else false

uuIiIsAdminUser(*isAdminUser) {
	*isAdminUser = false;
	foreach(*row in SELECT USER_TYPE WHERE USER_NAME = '$userNameClient' AND USER_TYPE = 'rodsadmin') {
		*isAdminUser = true;
	}
}


