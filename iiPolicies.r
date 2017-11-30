# This policy is fired when a file is put onto iRODS. 
acPostProcForPut {
	on ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Check for locks in the research area
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}

		iiCanDataObjCreate($objPath, *allowed, *reason);
		if (!*allowed) {
			# There is no acPreProcForPut, so we can only remove the object after the fact.
			msiDataObjUnlink("objPath=$objPath++++forceFlag=", *status);	
		}
	}

	on ($objPath like regex "/[^/]+/" ++ IIXSDCOLLECTION ++ "/.*\.xsd") {
		# Check new XSD against a schema for xsd validity. Rename the file when invalid

		*xsdpath =  "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/schema-for-xsd.xsd";		
		iiRenameInvalidXML($objPath, *xsdpath);
	}

	on ($objPath like regex "/[^/]+/" ++ IIFORMELEMENTSCOLLECTION ++ "/.*\.xml") {
		# Check  for invalid formelements XML files and rename them.
		*xsdpath =  "/" ++ $rodsZoneClient ++ IIXSDCOLLECTION ++ "/schema-for-formelements.xsd";		
		iiRenameInvalidXML($objPath, *xsdpath);
	}

}

# This policy is fired before a collection is deleted.
# The policy prohibits deleting the collection if the collection
# is locked
acPreprocForRmColl {
	on($collName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Check for locks in the research area
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
		#DEBUG writeLine("serverLog", "acPreprocForCollCreate: $collName");
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
	on($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".[^/]*/.*") {
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

		#DEBUG writeLine("serverLog", "acPreprocForDataObjOpen: $objPath");
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
	on (
	(*SourceItemType == "-C" || *SourceItemType == "-d")
	&& (*SourceItemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*"
	|| *TargetItemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*")
	) {

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

# This policy is fired when AVU metadata is added or set.
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
	on (*attributeName like UUUSERMETADATAPREFIX ++ "*" 
	    && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		uuGetUserType(uuClientFullName, *userType);
		if (*userType == "rodsadmin") {
			succeed;
		}

		# Only allow manipulation of user metadata when the target is not locked
		iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason);
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
        on (*attributeName == IISTATUSATTRNAME && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Special rules for the folder status. Subfolders and ancestors  of a special folder are locked.
		*actor = uuClientFullName;
		uuGetUserType(*actor, *userType);
		if (*userType == "rodsadmin") {
			*allowed = true;
		} else {	
			#DEBUG writeLine("serverLog", "Calling iiCanModifyFolderStatus");
			iiCanModifyFolderStatus(*option, *itemName, *attributeName, *attributeValue, *actor, *allowed, *reason);
		}
		if (*allowed) {
			iiFolderStatus(*itemName, *currentStatus);
			if (*option == "rm") {
				*newStatus = FOLDER;
			} else {
				*newStatus = *attributeValue;
			}
			*err = errorcode(iiPreFolderStatusTransition(*itemName, *currentStatus, *newStatus));
			if (*err < 0) {
				# Perhaps a rollback is needed
				*allowed = false;
			}
		}
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
        on (*attributeName == IIVAULTSTATUSATTRNAME && *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		# Special rules for the folder status. Subfolders and ancestors  of a special folder are locked.
		*actor = uuClientFullName;
		uuGetUserType(*actor, *userType);
		if (*userType == "rodsadmin") {
			*allowed = true;
		}

		if (*allowed) {
			iiVaultStatus(*itemName, *currentStatus);
			*newStatus = *attributeValue;
			*err = errorcode(iiPreVaultStatusTransition(*itemName, *currentStatus, *newStatus));
			if (*err < 0) {
				# Perhaps a rollback is needed
				*allowed = false;
			}
		}
		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}

# This policy gets triggered when metadata is modified
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit,  *newAttributeName, *newAttributeValue, *newAttributeUnit) {
	on (*attributeName like UUUSERMETADATAPREFIX ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*" ) {
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
        on (*attributeName == IISTATUSATTRNAME ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*" ) {
		*actor = uuClientFullName;
		uuGetUserType(*actor, *userType);
		if (*userType == "rodsadmin") {
			*allowed = true;
		} else {
			iiCanModifyFolderStatus(*option, *itemName, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue, *actor, *allowed, *reason); 
		}
		if (*allowed) {
			iiFolderStatus(*itemName, *currentStatus);
			*newStatus = triml(*newAttributeValue, "v:");
			*err = errorcode(iiPreFolderStatusTransition(*itemName, *currentStatus, *newStatus));
			if (*err < 0) {
				# Rollback
				*allowed = false;
			}
		}

		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
        on (*attributeName == IIVAULTSTATUSATTRNAME ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*" ) {
		*actor = uuClientFullName;
		uuGetUserType(*actor, *userType);
		if (*userType == "rodsadmin") {
			*allowed = true;
		}

		if (*allowed) {
			iiVaultStatus(*itemName, *currentStatus);
			*newStatus = triml(*newAttributeValue, "v:");
			*err = errorcode(iiPreVaultStatusTransition(*itemName, *currentStatus, *newStatus));
			if (*err < 0) {
				# Rollback
				*allowed = false;
			}
		}

		if (!*allowed) {
			cut;
			msiOprDisallowed;
		}
	}
}


acPostProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
        on (*attributeName == IISTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		if (*option == "rm") {
		       	*newStatus = FOLDER;
	       	} else {
		       	*newStatus =  *attributeValue;
	       	};
		iiPostFolderStatusTransition(*itemName, uuClientFullName, *newStatus);
	}
        on (*attributeName == IIVAULTSTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		iiPostVaultStatusTransition(*itemName, uuClientFullName, *attributeValue);
	}
}

acPostProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit,  *newAttributeName, *newAttributeValue, *newAttributeUnit) {
        on (*attributeName == IISTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		*newStatus = triml(*newAttributeValue, "v:");
		iiPostFolderStatusTransition(*itemName, uuClientFullName, *newStatus);	
	}
        on (*attributeName == IIVAULTSTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		*newStatus = triml(*newAttributeValue, "v:");
		iiPostVaultStatusTransition(*itemName, uuClientFullName, *newStatus);
	}
}


# \brief uuResourceModifiedPostResearch   	Policy to import metadata when a IIMETADATAXMLNAME file appears
# \param[in] *pluginInstanceName		A copy of $pluginInstanceName
# \param[in] KVPairs  a copy of $KVPairs
uuResourceModifiedPostResearch(*pluginInstanceName, *KVPairs) {
	# possible match
	# "/tempZone/home/research-any/possible/path/to/yoda-metadata.xml"
	# "/tempZone/home/datamanager-category/vault-path/to/yoda-metadata.xml"
	if (*KVPairs.logical_path like regex "^/"
	    ++ *KVPairs.client_user_zone
	    ++ "/home/"
	    ++ "(" ++ IIGROUPPREFIX ++ "|datamanager-)"
	    ++ "[^/]+(/.\*)\*/" ++ IIMETADATAXMLNAME ++ "$") {
		#DEBUG writeLine("serverLog", "uuResourceModifiedPostResearch:\n KVPairs = *KVPairs\npluginInstanceName = *pluginInstanceName");
		iiMetadataXmlModifiedPost(*KVPairs.logical_path, *KVPairs.client_user_name, *KVPairs.client_user_zone);
	}
}

# \brief uuResourceRenamePostResearch    This policy is created to support the moving, renaming and trashing of the .yoda-metadata.xml file as well as enforcing group ACL's when collections or data objects are moved from outside a research group into it
# \param[in] pluginInstanceName   a copy of $pluginInstanceName
# \param[in] KVPairs  a copy of $KVPairs
uuResourceRenamePostResearch(*pluginInstanceName, *KVPairs) {
	# example match "/mnt/irods01/vault01/home/research-any/possible/path/to/yoda-metadata.xml"
	#DEBUG writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
	*zone = *KVPairs.client_user_zone;
	*dst = *KVPairs.logical_path;
	iiLogicalPathFromPhysicalPath(*KVPairs.physical_path, *src, *zone);

	if (*dst like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		*srcPathElems = split(*src, "/");
		*dstPathElems = split(*dst, "/");		
		
		if (elem(*srcPathElems, 2) != elem(*dstPathElems, 2)) {
			uuEnforceGroupAcl(*dst);
		}
	
	}

	if (*src like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*/" ++ IIMETADATAXMLNAME ++ "$") {
		iiMetadataXmlRenamedPost(*src, *dst, *zone);

	}
}

# \brief uuResourceUnregisteredPostResearch	Policy to act upon the removal of a METADATAXMLNAME file.
# \param[in] pluginInstanceName   a copy of $pluginInstanceName
# \param[in] KVPairs  a copy of $KVPairs
uuResourceUnregisteredPostResearch(*pluginInstanceName, *KVPairs) {
	# Example match: "/tempZone/home/research-any/possible/path/to/yoda-metadata.xml"
	if (*KVPairs.logical_path like regex "^/"
	    ++ *KVPairs.client_user_zone
	    ++ "/home/" ++ IIGROUPPREFIX 
	    ++ "[^/]+(/.\*)\*/"
	    ++ IIMETADATAXMLNAME ++ "$") {

		#DEBUG writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		iiMetadataXmlUnregisteredPost(*KVPairs.logical_path);
		}
}
