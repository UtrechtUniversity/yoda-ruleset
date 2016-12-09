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
	uuGetUserType("$userNameClient#$rodsZoneClient", *userType);
	if (*userType == "rodsadmin") {
		*isAdminUser = true;
	} else {
		*isAdminUser = false;
	}
	*isAdminUser = false;
	foreach(*row in SELECT USER_TYPE WHERE USER_NAME = '$userNameClient' AND USER_TYPE = 'rodsadmin') {
		*isAdminUser = true;
	}
}

# \brief pep_resource_modified_post  	Policy to set the datapackage flag in case a DPTXTNAME file appears. This
#					dynamic PEP was chosen because it works the same no matter if the file is
#					created on the web disk or by a rule invoked in the portal. Also works in case the file is moved.
# \param[in,out] out	This is a required argument for Dynamic PEP's in the 4.1.x releases. It is unused.
pep_resource_modified_post(*out) {
	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";")) && ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
#		writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		uuChopPath($KVPairs.logical_path, *parent, *basename);	
		writeLine("serverLog", "pep_resource_modified_post: *basename added to *parent. Promoting to Datapackage");
		iiSetCollectionType(*parent, "Datapackage");
	}
}

# \brief pep_resource_rename_post	This policy is created to support the moving, renaming and trashing of the .yoda-datapackage.txt file
# \param[in,out] out			This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_rename_post(*out) {
	# run only at the top of the resource hierarchy and when a DPTXTNAME file is found inside a research group.
	# Unfortunately the source logical_path is not amongst the available data in $KVPairs. The physical_path does include the old path, but not in a convenient format.
	# When a DPTXTNAME file gets moved into a new directory it will be picked up by pep_resource_modified_post. So we don't need to set the Datapackage flag here.
        # This rule only needs to handle the degradation of the Datapackage to a folder when it's moved or renamed.

	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.physical_path like regex ".\*/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
		# writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		# the logical_path in $KVPairs is that of the destination
		uuChopPath($KVPairs.logical_path, *dest_parent, *dest_basename);
		# The physical_path is that of the source, but includes the path of the vault. If the vault path includes a home folder, we are screwed.
		*src_parent = trimr($KVPairs.physical_path, "/");
		*src_parent_lst = split(*src_parent, "/");
		# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
		uuListIndexOf(*src_parent_lst, "home", *idx);
		if (*idx < 0) {
			failmsg(-1,"pep_resource_rename_post: Could not find home in $KVPairs.physical_path. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		}
		# skip to the part of the path starting from ../home/..
		for( *el = 0; *el < *idx; *el = *el + 1){
			*src_parent_lst = tl(*src_parent_lst);
		}
		# Prepend with the zone and rejoin to a src_path
		*src_parent_lst	= cons($KVPairs.client_user_zone, *src_parent_lst);
		uuJoin("/", *src_parent_lst, *src_parent);
		*src_parent = "/" ++ *src_parent;
		writeLine("serverLog", "pep_resource_rename_post: \*src_parent = *src_parent");

		if (*dest_basename != DPTXTNAME && *src_parent == *dest_parent) {
			writeLine("serverLog", "pep_resource_rename_post: .yoda-datapackage.txt was renamed to *dest_basename. *src_parent loses datapackage flag.");
			iiSetCollectionType(*parent, "Folder");
		} else if (*src_parent != *dest_parent) {
			# The DPTXTNAME file was moved to another folder or trashed. Check if src_parent still exists and degrade it.
			if (uuCollectionExists(*src_parent)) {
				iiSetCollectionType(*src_parent, "Folder");
				writeLine("serverLog", "pep_resource_rename_post: " ++ DPTXTNAME ++ " was moved to *dest_parent. *src_parent became an ordinary Folder.");
			} else {
				writeLine("serverLog", "pep_resource_rename_post: " ++ DPTXTNAME ++ " was moved to *dest_parent and *src_parent is gone.");
			}
		}
	}
}

# \brief pep_resource_unregistered_post		Policy to act upon the removal of a DPTXTNAME file.
# \param[in,out] out 				This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_unregistered_post(*out) {
	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$")) {
		# writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		uuChopPath($KVPairs.logical_path, *parent, *basename);
		if (uuCollectionExists(*parent)) {
			writeLine("serverLog", "pep_resource_unregistered_post: Demoting *parent to Folder after removal of *basename");
			iiSetCollectionType(*parent, "Folder");
		} else {
			writeLine("serverLog", "pep_resource_unregistered_post: *basename was removed, but *parent is also gone.");
		}			
	}
}

# \brief acPostProcForCollCreate 		Policy to mark Collections as Folder or Research Team when created.
acPostProcForCollCreate {
	on ($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+\$") {
		writeLine("serverLog", "acPostProcForCollCreate: A Research team is created at $collName");
		
		iiSetCollectionType($collName, "Research Team");
	}
       	on ($collName like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]\*/.\*") {
		writeLine("serverLog", "acPostProcForCollCreate: an ordinary folder is created at $collName");
		iiSetCollectionType($collName, "Folder");
	}
}
