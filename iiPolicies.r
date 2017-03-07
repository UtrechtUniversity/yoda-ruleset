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

# This policy is fired before a collection is deleted.
# The policy prohibits deleting the collection if the collection
# is locked
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

# This policy is fired before a data object is deleted
# The policy prohibits deleting the data object if the data object
# is locked. The parent collection is not checked
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

# This policy is fired before a collection is created
# The policy prohibits creating a new collection if the
# parent collection is locked
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

# This policy is fired before a data object is renamed or moved
# The policy disallows renaming or moving the data object, if the
# object is locked, or if the collection that will be the new parent
# collection of the data object after the rename is locked
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

# This policy is fired before a data object is opened.
# The policy does not prohibit opening data objects for reading,
# but if the data object is locked, opening for writing is 
# disallowed. Many editors open a file for reading while editing and
# store the file locally. Only when saving the changes, the file is
# opened for writing. IF the file is locked, this means changes can be
# created in the file, but they cannot be saved.
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

# This policy is fired if AVU meta data is copied from one object to another.
# Copying of metadata is prohibited by this policy if the target object is locked
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
				iiFolderTransition(*itemName, *currentStatus, *attributeValue);
			}
		} else {
			*allowed = true;
			# iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason);
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
				iiFolderTransition(*itemName, *currentStatus,*attributeValue);
			}

		} else {
			iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) ;
		}
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}

# \brief pep_resource_modified_post  	Policy to import metadata when a IIMETADATAXMLNAME file appears. This
#					dynamic PEP was chosen because it works the same no matter if the file is
#					created on the web disk or by a rule invoked in the portal. Also works in case the file is moved.
# \param[in,out] out	This is a required argument for Dynamic PEP's in the 4.1.x releases. It is unused.
pep_resource_modified_post(*out) {
	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";")) && ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$")) {
		writeLine("serverLog", "pep_resource_modified_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		uuChopPath($KVPairs.logical_path, *parent, *basename);
		writeLine("serverLog", "pep_resource_modified_post: *basename added to *parent. Import of metadata started");
		iiPrepareMetadataImport($KVPairs.logical_path, $KVPairs.client_user_zone, *xsdpath, *xslpath);
		*err = errormsg(msiXmlDocSchemaValidate($KVPairs.logical_path, *xsdpath, *status_buf), *msg);
		if (*err < 0) {
			writeLine("serverLog", *msg);
		} else if (*err == 0) {
			writeLine("serverLog", "XSD validation successful. Start indexing");
			iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
			iiImportMetadataFromXML($KVPairs.logical_path, *xslpath);
		} else {
			writeBytesBuf("serverLog", *status_buf);
		}
	}
}

# \brief pep_resource_modified_post 	Create revisions on file modifications
# \description				This policy should trigger whenever a new file is added or modified
#					in the workspace of a Research team. This should be done asynchronously
# \param[in,out] out	This is a required argument for Dynamic PEP's in the 4.1.x releases. It is unused.
#pep_resource_modified_post(*out) {
#	on ($pluginInstanceName == hd(split($KVPairs.resc_hier, ";")) && ($KVPairs.logical_path like "/" ++ $KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "*") ) {
#		*path = $KVPairs.logical_path;
#		uuChopPath(*path, *parent, *basename);
#		if (*basename like "._*") {
#			writeLine("serverLog", "pep_resource_modified_post: Ignore *basename for revision store. This is littering by Mac OS");
#		} else {
#			uuRevisionCreateAsynchronously(*path);
#		}
#	}
#}

# \brief pep_resource_rename_post	This policy is created to support the moving, renaming and trashing of the .yoda-metadata.xml file
# \param[in,out] out			This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_rename_post(*out) {
	# run only at the top of the resource hierarchy and when a IIMETADATAXMLNAME file is found inside a research group.
	# Unfortunately the source logical_path is not amongst the available data in $KVPairs. The physical_path does include the old path, but not in a convenient format.
	# When a IIMETADATAXMLNAME file gets moved into a new directory it will be picked up by pep_resource_modified_post.
	# This rule only needs to handle the removal of user metadata when it's moved or renamed.

	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.physical_path like regex ".\*/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$")) {
		writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		# the logical_path in $KVPairs is that of the destination
		uuChopPath($KVPairs.logical_path, *dest_parent, *dest_basename);
		# The physical_path is that of the source, but includes the path of the vault. If the vault path includes a home folder, we are screwed.
		*src_parent = trimr($KVPairs.physical_path, "/");
		*src_parent_lst = split(*src_parent, "/");
		# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
		uuListIndexOf(*src_parent_lst, "home", *idx);
		if (*idx < 0) {
			writeLine("serverLog","pep_resource_rename_post: Could not find home in $KVPairs.physical_path. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
			succeed;
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

		if (*dest_basename != IIMETADATAXMLNAME && *src_parent == *dest_parent) {
			writeLine("serverLog", "pep_resource_rename_post: " ++ IIMETADATAXMLNAME ++ " was renamed to *dest_basename. *src_parent loses user metadata.");
			iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
		} else if (*src_parent != *dest_parent) {
			# The IIMETADATAXMLNAME file was moved to another folder or trashed. Check if src_parent still exists and Remove user metadata.
			if (uuCollectionExists(*src_parent)) {
				iiRemoveAVUs(*src_parent, UUUSERMETADATAPREFIX);
				writeLine("serverLog", "pep_resource_rename_post: " ++ IIMETADATAXMLNAME ++ " was moved to *dest_parent. Remove User Metadata from *src_parent.");
			} else {
				writeLine("serverLog", "pep_resource_rename_post: " ++ IIMETADATAXMLNAME ++ " was moved to *dest_parent and *src_parent is gone.");
			}
		}
	}
}

# \brief pep_resource_unregistered_post		Policy to act upon the removal of a METADATAXMLNAME file.
# \param[in,out] out 				This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_unregistered_post(*out) {
	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$")) {
		# writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = $KVPairs\n\$pluginInstanceName = $pluginInstanceName\n \$status = $status\n \*out = *out");
		uuChopPath($KVPairs.logical_path, *parent, *basename);
		if (uuCollectionExists(*parent)) {
			writeLine("serverLog", "pep_resource_unregistered_post: *basename removed. Removing user metadata from *parent");
			iiRemoveAVUs(*parent, UUUSERMETADATAPREFIX);
		} else {
			writeLine("serverLog", "pep_resource_unregistered_post: *basename was removed, but *parent is also gone.");
		}			
	}
}
