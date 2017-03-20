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
				*err = errorcode(iiFolderTransition(*itemName, *currentStatus, *attributeValue));
				if (*err < 0) {
					# Rollback
					*allowed = false;
				}
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
				*err = errorcode(iiFolderTransition(*itemName, *currentStatus,*attributeValue));
				if (*err < 0) {
					# Rollback
					*allowed = false;
				}
			}

		} else {
			*allowed = true;
			#iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) ;
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
		iiMetadataXmlModifiedPost($KVPairs.logical_path, $KVPairs.client_user_zone);
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
		*zone =  $KVPairs.client_user_zone;
		*dst = $KVPairs.logical_path;
		iiLogicalPathFromPhysicalPath($KVPairs.physical_path, *src, *zone);
		iiMetadataXmlRenamedPost(*src, *dst, *zone);

}
}

# \brief pep_resource_unregistered_post		Policy to act upon the removal of a METADATAXMLNAME file.
# \param[in,out] out 				This is a required parameter for Dynamic PEP's in 4.1.x releases. It is not used by this rule.
pep_resource_unregistered_post(*out) {
	on (($pluginInstanceName == hd(split($KVPairs.resc_hier, ";"))) && ($KVPairs.logical_path like regex "^/" ++ $KVPairs.client_user_zone ++ "/home/" ++ IIGROUPPREFIX ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$")) {
		iiMetadataXmlUnregisteredPost($KVPairs.logical_path);
		}
}
