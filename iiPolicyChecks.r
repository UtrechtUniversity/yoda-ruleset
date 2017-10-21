# \brief iiRenameInvalidXML
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
				#DEBUG writeLine("serverLog", "*xmlpath validates");
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

# \brief iiIsStatusTransitionLegal
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

# \brief iiIsVaultStatusTransitionLegal
iiIsVaultStatusTransitionLegal(*fromstatus, *tostatus) {
	*legal = false;
	foreach(*legaltransition in IIVAULTTRANSITIONS) {
		(*legalfrom, *legalto) = *legaltransition;
		if (*legalfrom == *fromstatus && *legalto == *tostatus) {
			*legal = true;
			break;
		}
	}
	*legal;
}

# \brief iiGetLocks
iiGetLocks(*objPath, *locks) {
	*locks = list();
	*lockattrname = IILOCKATTRNAME;
	msiGetObjType(*objPath, *objType);
	if (*objType == '-d') {
		uuChopPath(*objPath, *collection, *dataName);
		foreach (*row in SELECT META_DATA_ATTR_VALUE
					WHERE COLL_NAME = *collection
					  AND DATA_NAME = *dataName
					  AND META_DATA_ATTR_NAME = *lockattrname
			) {
				*rootCollection= *row.META_DATA_ATTR_VALUE;
				*locks = cons(*rootCollection, *locks);
			}
	} else {
		foreach (*row in SELECT META_COLL_ATTR_VALUE
					WHERE COLL_NAME = *objPath
					  AND META_COLL_ATTR_NAME = *lockattrname
			) {
				*rootCollection = *row.META_COLL_ATTR_VALUE;
				*locks = cons(*rootCollection, *locks);
		}
	}
}

# \brief iiCanCollCreate 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanCollCreate(*path, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown failure";

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks);
	if (size(*locks) > 0) {
		foreach(*rootCollection in *locks) {
			if (strlen(*rootCollection) > strlen(*parent)) {
				*reason = "lock found on *parent, but Starting from *rootCollection" ;
				*allowed = true;
			} else {
				*reason = "lock found on *parent. Disallowing creating subcollection: *basename";
				*allowed = false;
				break;
			}
		}
	} else {
		*reason = "No locks found on *parent";
		*allowed = true;
	}

	#DEBUG writeLine("serverLog", "iiCanCollCreate: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollRename 
# \param[in] src
# \param[in] dst
# \param[out] allowed
# \param[out] reason
iiCanCollRename(*src, *dst, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks);
	if(size(*locks) > 0) {
		*allowed = false;
		*reason = "*src is has locks *locks";
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks);
		if (size(*locks) > 0) {
			foreach(*rootCollection in *locks) {
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent renaming subcollections.";
				} else {
					*allowed = false;
					*reason = "*dstparent has lock on *rootCollection";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No Locks found";
		}
	}

	#DEBUG writeLine("serverLog", "iiCanCollRename: *src -> *dst; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanCollDelete(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown error"; 	
	iiGetLocks(*path, *locks);
	if(size(*locks) > 0) {
		*allowed = false;
		*reason = "Locked with *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}

	#DEBUG writeLine("serverLog", "iiCanCollDelete: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjCreate(*path, *allowed, *reason) {
	
	*allowed = false;
	*reason = "Unknown error";

	uuChopPath(*path, *parent, *basename);
	iiGetLocks(*parent, *locks);
	if(size(*locks) > 0) {
		foreach(*rootCollection in *locks) {
			if (strlen(*rootCollection) > strlen(*parent)) {
				*allowed = true;
				*reason = "*parent has locked child *rootCollection, but this does not prevent creating new files.";
			} else {
				*allowed = false;
				*reason = "*parent has lock starting from *rootCollection";
				break;
			}
		}
	} else {
		*allowed = true;
		*reason = "No locks found";
	}

	#DEBUG writeLine("serverLog", "iiCanDataObjCreate: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjWrite(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown error";

	iiGetLocks(*path, *locks);
	if(size(*locks) > 0) {
		*allowed = false;
		*reason = "Locks found: *locks";
	} else  {
		uuChopPath(*path, *parent, *basename);
		iiGetLocks(*parent, *locks);
		if(size(*locks) > 0) {
			foreach(*rootCollection in *locks) {
				if (strlen(*rootCollection) > strlen(*parent)) {
					*allowed = true;
					*reason = "*parent has locked child *rootCollection, but this does not prevent writing to files.";
				} else {
					*allowed = false;
					*reason = "*parent has lock starting from *rootCollection";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}
	
	#DEBUG writeLine("serverLog", "iiCanDataObjWrite: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjRename(*src, *dst, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown error";
	iiGetLocks(*src, *locks);
	if(size(*locks) > 0) {
		*allowed = false;
		*reason = "*src is locked with *locks";
	} else {
		uuChopPath(*dst, *dstparent, *dstbasename);
		iiGetLocks(*dstparent, *locks);
		if(size(*locks) > 0) {
			foreach(*rootCollection in *locks) {
				if (strlen(*rootCollection) > strlen(*dstparent)) {
					*allowed = true;
					*reason = "*dstparent has locked child *rootCollection, but this does not prevent writing to files.";
				} else {
					*allowed = false;
					*reason = "*dstparent has lock starting from *rootCollection";
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	}

	#DEBUG writeLine("serverLog", "iiCanDataObjRename: *src -> *dst; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanDataObjDelete(*path, *allowed, *reason) {

	*allowed = false;
	*reason = "Unknown Error";

	iiGetLocks(*path, *locks);
	if(size(*locks) > 0) {
		*reason = "Found lock(s) *locks";
	} else {
		*allowed = true;
		*reason = "No locks found";
	}
	#DEBUG writeLine("serverLog", "iiCanDataObjDelete: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName, *allowed, *reason) {	
	*allowed = false;
	*reason = "Unknown error";
	
	if (*targetItemType == "-C") {	
		# Prevent copying metadata to locked folder
		iiGetLocks(*targetItemName, *locks);
		if (size(*locks) > 0) {
			foreach(*rootCollection in *locks) {
				if (strlen(*rootCollection) > strlen(*targetItemName)) {
					*allowed = true;
					*reason = "*rootCollection is locked, but does not affect metadata copy to *targetItemName";
				} else {
					*allowed = false;
					*reason = "*targetItemName is locked starting from *rootCollection";	
					break;
				}
			}
		} else {
			*allowed = true;
			*reason = "No locks found";
		}
	} else if (*targetItemType == "-d") {
		iiGetLocks(*targetItemName, *locks);
		if (size(*locks) > 0) {
			*reason = "*targetItemName has lock(s) *locks";
		} else {
			*allowed = true;
			*reason = "No locks found.";
		}
	} else {
		*allowed = true;
		*reason = "Restrictions only apply on Collections and DataObjects";
	}

	#DEBUG writeLine("serverLog", "iiCanCopyMetadata: *sourceItemName -> *targetItemName; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";

	iiGetLocks(*itemName, *locks);
	if (size(*locks) > 0) {
		if (*itemType == "-C") {
			foreach(*rootCollection in *locks) {
				if (strlen(*rootCollection) > strlen(*itemName)) {
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

	#DEBUG writeLine("serverLog", "iiCanModifyUserMetadata: *itemName; allowed=*allowed; reason=*reason");
}

# \brief iiCanCollDelete 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanModifyOrgMetadata(*option, *itemType, *itemName, *attributeName, *allowed, *reason) {
	*allowed = true;
	*reason = "No reason to lock OrgMetatadata yet";
	#DEBUG writeLine("serverLog", "iiCanModifyOrgMetadata: *itemName; allowed=*allowed; reason=*reason");
}

# \brief iiCanModifyFolderStatus 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *actor, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (*attributeName != IISTATUSATTRNAME) {
		*reason = "Called for attribute *attributeName instead of FolderStatus.";
		succeed;
	}

	if (*option == "rm") {
		*transitionFrom = *attributeValue;
		*transitionTo =  FOLDER;
	}

	if (*option == "add") {
		iiFolderStatus(*path, *transitionFrom);
		*transitionTo = *attributeValue;	

	}

	if (*option == "set") {
		iiFolderStatus(*path, *transitionFrom);
		*transitionTo = *attributeValue;
	}

	iiCanTransitionFolderStatus(*path, *transitionFrom, *transitionTo, *actor, *allowed, *reason); 

	#DEBUG writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanModifyFolderStatus 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *newAttributeName, *newAttributeValue, *actor, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (*newAttributeName == "" || *newAttributeName == IISTATUSATTRNAME ) {
		*transitionFrom = *attributeValue;
		*transitionTo = triml(*newAttributeValue, "v:");
		iiCanTransitionFolderStatus(*path, *transitionFrom, *transitionTo, *actor, *allowed, *reason);
	} else {
		*reason = "*attributeName should not be changed to *newAttributeName";
	}

	#DEBUG writeLine("serverLog", "iiCanModifyFolderStatus: *path; allowed=*allowed; reason=*reason");
}

# \brief iiCanTransitionFolderStatus 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanTransitionFolderStatus(*folder, *transitionFrom, *transitionTo, *actor, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (iiIsStatusTransitionLegal(*transitionFrom, *transitionTo)) {
		*allowed = true;
		*reason = "Legal status transition. *transitionFrom -> *transitionTo";
	} else {
		if (*transitionFrom == FOLDER) {
			*reason = "Illegal status transition. Current folder has no status.";
		} else {
			*reason = "Illegal status transition. Current status is *transitionFrom.";
		}
		succeed;
	}

	if (*transitionTo == SUBMITTED) {
		*xmlpath = *folder ++ "/" ++ IIMETADATAXMLNAME;
		*zone = hd(split(triml(*folder, "/"), "/"));
		*err = errorcode(iiPrepareMetadataImport(*xmlpath, *zone, *xsdpath, *xslpath));
		if (*err < 0) { 
			*allowed = false;
			*reason = "Folder submitted without metadata.";
			succeed;
		} else {
			*err = errormsg(msiXmlDocSchemaValidate(*xmlpath, *xsdpath, *status_buf), *msg);
			if (*err < 0) {
				*allowed = false;
				*reason = "Metadata does not conform to schema.";
				succeed;
			}
		}

	}

	if (*transitionTo == ACCEPTED || *transitionTo == REJECTED) {
		*err1 = errorcode(iiCollectionGroupName(*folder, *groupName));	
		*err2 = errorcode(uuGroupGetCategory(*groupName, *category, *subcategory));
		*err3 = errorcode(uuGroupExists("datamanager-*category", *datamanagerExists));
		if (*err1 < 0 || *err2 < 0 || *err3 < 0) {
			*allowed = false;
			*reason = "Could not determine if datamanager-*category exists";
			succeed;
		}	
		if (*datamanagerExists) {
			uuGroupGetMemberType("datamanager-*category", *actor, *userTypeIfDatamanager);	
			if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
				*allowed = true;
				*reason = "Folder is *transitionTo by *actor from datamanager-*category";
			} else {
				*allowed = false;
				*reason = "Only a member of datamanager-*category is allowed to accept or reject a submitted folder";
				succeed;
			}
		} else {
			*allowed = true;
			*reason = "When no datamanager group exists, submitted folders are automatically accepted";
		}
	}

	if (*transitionTo == SECURED) {
		*allowed = false;
		*reason = "Only a rodsadmin is allowed to secure a folder to the vault";
		succeed;
	}

	if (*allowed) {	
		iiGetLocks(*folder, *locks);
		if (size(*locks) > 0) {
			foreach(*rootCollection in *locks) {
				if (*rootCollection != *folder) {
					*allowed = false;
					*reason = "Found lock(s) starting from *rootCollection";
					break;
				}
			}
		}
	}
}


# \brief iiCanTransitionVaultStatus 
# \param[in] path
# \param[out] allowed
# \param[out] reason
iiCanTransitionVaultStatus(*folder, *transitionFrom, *transitionTo, *actor, *allowed, *reason) {
	*allowed = false;
	*reason = "Unknown error";
	if (iiIsVaultStatusTransitionLegal(*transitionFrom, *transitionTo)) {
		*allowed = true;
		*reason = "Legal status transition. *transitionFrom -> *transitionTo";
	} else {
		*reason = "Illegal status transition. Current status is *transitionFrom.";
		succeed;
	}

	if (*transitionTo == PUBLISHED) {
		iiGetDOIFromMetadata(*folder, *yodaDOI);	
		if (*yodaDOI == "") {
			*allowed = false;
			*reason = "*folder has no DOI"
			succeed;
		}

		iiGetLandingPageFromMetadata(*folder, *landingPage);
		if (*landingPage == "") {
			*allowed = false;
			*reason = "*folder has no landing page";
			succeed;
		}
	}
}
