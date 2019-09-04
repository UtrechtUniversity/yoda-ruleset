# \file      iiPolicies.r
# \brief     Policy Enforcement Points (PEP) used for the research area are defined here.
#            All processing or policy checks are defined in separate rules outside this file.
#            The arguments and session variables passed to the PEP's are defined in iRODS itself.
# \author    Paul Frederiks
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

# \brief This policy is fired when a file is put onto iRODS. In the research area we need to check
#         for locks. To prevent breaking the metadata form, whenever an XSD is
#         uploaded it is validated against a schema for XSD validity.
#
acPostProcForPut {
	if ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Check for locks in the research area.
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
	else if ($objPath like regex "/[^/]+/" ++ IISCHEMACOLLECTION ++ "/.*\.xsd") {
		# Check new XSD against a schema for xsd validity. Rename the file when invalid.
		*xsdpath =  "/" ++ $rodsZoneClient ++ IISCHEMACOLLECTION ++ "/schema-for-xsd.xsd";
		iiRenameInvalidXML($objPath, *xsdpath);
	}
}

# \brief This policy is fired before a collection is deleted.
#        The policy prohibits deleting the collection if the collection
#        is locked
#
acPreprocForRmColl {
	if ($collName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Check for locks in the research area.
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

# \brief  This policy is fired before a data object is deleted
#         The policy prohibits deleting the data object if the data object
#         is locked. The parent collection is not checked
#
acDataDeletePolicy {
	if ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		# Check for locks in the research area.
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

# \brief  This policy is fired before a collection is created. The policy prohibits creating
#         a new collection if the parent collection is locked
#
acPreprocForCollCreate {
	if ($collName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
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

# \brief  This policy is fired before a data object is renamed or moved
#         The policy disallows renaming or moving the data object, if the
#         object is locked, or if the collection that will be the new parent
#         collection of the data object after the rename is locked
#
acPreProcForObjRename(*src, *dst) {
	if ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".[^/]*/.*") {
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

        if($objPath like regex "/[^/]+/home/" ++ ".[^/]*") {
                uuGetUserType(uuClientFullName, *userType);
                if (*userType != "rodsadmin") {
                        cut;
                        msiOprDisallowed;
                }
        }
}


# \brief  This policy is fired before a data object is opened.
#         The policy does not prohibit opening data objects for reading,
#         but if the data object is locked, opening for writing is
#         disallowed. Many editors open a file for reading while editing and
#         store the file locally. Only when saving the changes, the file is
#         opened for writing. If the file is locked, this means changes can be
#         created in the file, but they cannot be saved.
#
acPreprocForDataObjOpen {
	if ($writeFlag == "1" && $objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
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

# \brief  This policy is fired when AVU meta data is copied from one object to another.
#         Copying of metadata is prohibited by this policy if the target object is locked
#
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) {
	if (
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

# \brief  This policy is fired when AVU metadata is added or set. Status transitions for folders and vault packages are
#         implemented as AVU metadata changes on attributes defined in iiConstants.r
#         When the status metadata is changed Pre condition transition rules are called in iiFolderStatusTransitsions.r and
#         iiVaultTransitions.r
#         Organisational metadata is needed for these status transitions and actions belonging to them. So we can't lock
#         the organisational metadata when a folder is locked.
#
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
	if (*attributeName like UUUSERMETADATAPREFIX ++ "*"
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

        else if (*attributeName == IISTATUSATTRNAME && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
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

        else if (*attributeName == IIVAULTSTATUSATTRNAME && *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
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

# \brief This policy gets triggered when metadata is modified. This cannot be triggered from a rule as the
#        current set of microservices have no 'mod' variant. When imeta is used however, the behaviour should
#        be the same for locked folders and folder transitions as the PEP above.
#
acPreProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit,  *newAttributeName, *newAttributeValue, *newAttributeUnit) {
	if (*attributeName like UUUSERMETADATAPREFIX ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*" ) {
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

        else if (*attributeName == IISTATUSATTRNAME ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*" ) {
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

        else if (*attributeName == IIVAULTSTATUSATTRNAME ++ "*" && *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*" ) {
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

# \brief  This PEP is called after a AVU is added (option = 'add'), set (option = 'set') or removed (option = 'rm') in the research area or the vault. Post conditions
#         defined in iiFolderStatusTransitions.r and iiVaultTransitions.r are called here.
acPostProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
        if (*attributeName == IISTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		if (*option == "rm") {
		       	*newStatus = FOLDER;
	       	} else {
		       	*newStatus =  *attributeValue;
	       	};
		iiPostFolderStatusTransition(*itemName, uuClientFullName, *newStatus);
	}

        else if (*attributeName == IIVAULTSTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		iiPostVaultStatusTransition(*itemName, uuClientFullName, *attributeValue);
	}
}

# \brief This PEP is called after an AVU is modified (option = 'mod') in the research area or the vault. Post conditions are called
#        in iiFolderStatusTransitions.r and iiVaultTransitions.r
acPostProcForModifyAVUMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit,  *newAttributeName, *newAttributeValue, *newAttributeUnit) {
        if (*attributeName == IISTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*") {
		*newStatus = triml(*newAttributeValue, "v:");
		iiPostFolderStatusTransition(*itemName, uuClientFullName, *newStatus);
	}

        else if (*attributeName == IIVAULTSTATUSATTRNAME &&  *itemName like regex "/[^/]+/home/" ++ IIVAULTPREFIX ++ ".*") {
		*newStatus = triml(*newAttributeValue, "v:");
		iiPostVaultStatusTransition(*itemName, uuClientFullName, *newStatus);
	}
}


# \brief uuResourceModifiedPostResearch  Policy to import metadata when a IIJSONMETADATA file appears. Instance specific rulesets
#                                        should call this rule from the appropriate dynamic PEP. As the call signatures for dynamic PEPs
#                                        are in flux between iRODS versions, these rules should be changed.
# \param[in] pluginInstanceName		 a copy of $pluginInstanceName from the dynamic PEP
# \param[in] KVPairs                     a copy of $KVPairs from the dynamic PEP
uuResourceModifiedPostResearch(*pluginInstanceName, *KVPairs) {
	# possible match
	# "/tempZone/home/research-any/possible/path/to/yoda-metadata.json"
	# "/tempZone/home/vault-any/possible/path/to/yoda-metadata[123][1].json"
	# "/tempZone/home/datamanager-category/vault-path/to/yoda-metadata.json"
	# writeLine("serverLog", "uuResourceModifiedPostResearch:\n KVPairs = *KVPairs\npluginInstanceName = *pluginInstanceName");

	uuChopFileExtension(IIJSONMETADATA, *jsonMetaName, *jsonExt);
	*vaultJsonRegex = "^/" ++ *KVPairs.user_rods_zone
	               ++  "/home/" ++ IIVAULTPREFIX ++ "[^/]+/.+"
	               ++ "/*jsonMetaName\\[[^/]+\\].*jsonExt$";

	# JSON changed in research or datamanager staging area?
	if (*KVPairs.logical_path like regex "^/"
	    ++ *KVPairs.user_rods_zone
	    ++ "/home/"
	    ++ "(" ++ IIGROUPPREFIX ++ "|datamanager-)"
	    ++ "[^/]+(/.\*)\*/" ++ IIJSONMETADATA ++ "$"
	    # Or in the vault?
     || *KVPairs.logical_path like regex *vaultJsonRegex) {

		writeLine("serverLog", "uuResourceModifiedPostResearch: Metadata JSON at <"
		       ++ *KVPairs.logical_path ++ "> updated by " ++ uuClientFullName
		       ++ ", ingesting");

		iiMetadataJsonModifiedPost(*KVPairs.logical_path, *KVPairs.user_user_name, *KVPairs.user_rods_zone);
    }
}

# \brief This PEP is called whenever a data object or collection is renamed or moved.
#        Will enforce the ACL's of a research or grp group when data is moved from outside the group.
acPostProcForObjRename(*src, *dst) {
	if (*dst like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".[^/]*/.*") {
		# enforce research group ACL's on folder moved from outside of research group
		*srcPathElems = split(*src, "/");
		*dstPathElems = split(*dst, "/");
		#DEBUG writeLine("serverLog", "acPostProcForObjRename: *src -> *dst");
		if (elem(*srcPathElems, 2) != elem(*dstPathElems, 2)) {
			uuEnforceGroupAcl(*dst);
		}
	}
	else if (*dst like regex "/[^/]+/home/" ++ IIGRPPREFIX ++ ".[^/]*/.*") {
		# enforce grp group ACL's on folder moved from outside of grp group
		*srcPathElems = split(*src, "/");
		*dstPathElems = split(*dst, "/");
		#DEBUG writeLine("serverLog", "acPostProcForObjRename: *src -> *dst");
		if (elem(*srcPathElems, 2) != elem(*dstPathElems, 2)) {
			uuEnforceGroupAcl(*dst);
		}
	}
}

# \brief This policy is created to support the moving, renaming
#        and trashing of the .yoda-metadata.xml file as well as
#        enforcing group ACL's when collections or data objects
#        are moved from outside a research group into it.
#
# \param[in] pluginInstanceName  a copy of $pluginInstanceName
# \param[in] KVPairs             a copy of $KVPairs
#
uuResourceRenamePostResearch(*pluginInstanceName, *KVPairs) {
	# example match "/mnt/irods01/vault01/home/research-any/possible/path/to/yoda-metadata.xml"
	#DEBUG writeLine("serverLog", "pep_resource_rename_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
	*zone = *KVPairs.user_rods_zone;
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

# \brief Policy to act upon the removal of a METADATAXMLNAME file.
#
# \param[in] pluginInstanceName   a copy of $pluginInstanceName
# \param[in] KVPairs  a copy of $KVPairs
#
uuResourceUnregisteredPostResearch(*pluginInstanceName, *KVPairs) {
	# Example match: "/tempZone/home/research-any/possible/path/to/yoda-metadata.xml"
	if (*KVPairs.logical_path like regex "^/"
	    ++ *KVPairs.user_rods_zone
	    ++ "/home/" ++ IIGROUPPREFIX
	    ++ "[^/]+(/.\*)\*/"
	    ++ IIMETADATAXMLNAME ++ "$") {

		#DEBUG writeLine("serverLog", "pep_resource_unregistered_post:\n \$KVPairs = *KVPairs\n\$pluginInstanceName = *pluginInstanceName");
		iiMetadataXmlUnregisteredPost(*KVPairs.logical_path);
	}
}
