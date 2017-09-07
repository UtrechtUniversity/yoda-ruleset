# \file iiVaultTransitions.r
# \brief Copy folders to the vault
#
# \copyright Copyright (c) 2017, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE


# \brief iiVaultStatus Retrieve current vault folder status
# \param[in]  folder	    Path of vault folder
# \param[out] folderStatus  Current status of vault folder
iiVaultStatus(*folder, *vaultStatus) {
	*vaultStatusKey = IIVAULTSTATUSATTRNAME;
	*vaultStatus = UNPUBLISHED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *vaultStatusKey) {
		*vaultStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief iiVaultGetActionActor Retrieve actor of action on vault folder
# \param[in]  folder      Path of action vault folder
# \param[out] actionActor Actor of action on vault folder
iiVaultGetActionActor(*folder, *actor, *actionActor) {
	# Retrieve vault folder collection id.
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
	        *collId = *row.COLL_ID;
	}

	# Retrieve vault folder action actor.
	*actionActor = "";
        foreach(*row in SELECT COLL_ID, META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = "org_vault_action_*collId") {
	         msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actionActor, "get", 2);
		 succeed;
	}

	# Fallback actor (rodsadmin).
        if (*actionActor == "") {
                *actionActor = *actor;
        }
}

# \brief iiPreVaultStatusTransition  Actions taken before vault status transition
# \param[in] folder            Path of vault folder
# \param[in] currentStatus     Current status of vault folder
# \param[in] newStatus         New status of vault folder
iiPreVaultStatusTransition(*folder, *currentVaultStatus, *newVaultStatus) {
	on (*currentVaultStatus == SUBMITTED_FOR_PUBLICATION && *newVaultStatus == UNPUBLISHED) {
		*actor = uuClientFullName;
	        iiVaultGetActionActor(*folder, *actor, *actionActor);
		iiAddActionLogRecord(*actionActor, *folder, "canceled publication");
	}
	on (*newVaultStatus == PUBLISHED) {
		# TODO prepare for publication
	}
	on (*newVaultStatus == DEPUBLISHED) {
		# TODO prepare for depublication
	}
	on (true) {
		nop;
	}
}

# \brief iiVaultRequestStatusTransition   Request vault status transition action
# \param[in] folder
# \param[in] newFolderStatus
# \param[in] actor
iiVaultRequestStatusTransition(*folder, *newVaultStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	# Determine vault group and actor.
	*pathElems = split(*folder, "/");
	*rodsZone = elem(*pathElems, 0);
        *vaultGroup = elem(*pathElems, 2);
	*actor = uuClientFullName;

	# Check if user is manager of research group.
	iiCollectionGroupNameAndUserType(*folder, *actorGroup, *userType, *isDatamanager);

	# Status SUBMITTED_FOR_PUBLICATION can only be requested by researcher.
	if (*newVaultStatus == SUBMITTED_FOR_PUBLICATION && !*isDatamanager) {
		*actorGroupPath = "/*rodsZone/home/*actorGroup";
	# Status UNPUBLISHED can be called by researcher and datamanager.
	} else 	if (*newVaultStatus == UNPUBLISHED && !*isDatamanager) {
		*actorGroupPath = "/*rodsZone/home/*actorGroup";
	} else 	if (*isDatamanager) {
		iiDatamanagerGroupFromVaultGroup(*vaultGroup, *actorGroup);
		*actorGroupPath = "/*rodsZone/home/*actorGroup";
	}

	# Retrieve collection id.
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
		*collId = *row.COLL_ID;
	}

	# Add vault action request to datamanager group.
	writeLine("serverLog", "iiVaultRequestStatusTransition: *newVaultStatus on *folder by *actor");
	*json_str = "[\"*folder\", \"*newVaultStatus\", \"*actor\"]";
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_action_" ++ "*collId=" ++ *json_str, *kvp);
	*err = errormsg(msiAssociateKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"), *msg);
	if (*err < 0) {
		*status = "Unrecoverable";
		*statusInfo = "*err - *msg";
		succeed;
        }

	# Add vault action status to datamanager group.
	# Used in frontend to check if vault package is in state transition.
	*vaultStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId=PENDING";
	msiString2KeyValPair(*vaultStatus, *kvp);
	*err = errormsg(msiAssociateKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"), *msg);
	if (*err < 0) {
		*status = "Unrecoverable";
		*statusInfo = "*err - *msg";
		succeed;
	} else {
		*status = "Success";
		*statusInfo = "";
		succeed;
	}
}

# \brief iiVaultProcessStatusTransition   Processing vault status transition request
# \param[in] folder
# \param[in] newFolderStatus
# \param[in] actor
iiVaultProcessStatusTransition(*folder, *newFolderStatus, *actor, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		writeLine("stdout", "iiVaultStatusTransition: Should only be called by a rodsadmin");
		fail;
	}

	# Set new vault status.
	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ *newFolderStatus;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, *newFolderStatus, *actor, *allowed, *reason);
		if (!*allowed) {
			*status = "PermissionDenied";
			*statusInfo = *reason;
		} else {
			if (*err == -818000) {
				*status = "PermissionDenied";
				*statusInfo = "User is not permitted to modify folder status";
			} else {
				*status = "Unrecoverable";
				*statusInfo = "*err - *msg";
			}
		}
        } else {
		*status = "Success";
		*statusInfo = "";
	}
}

# \brief iiPostVaultStatusTransition   Processing after vault status is changed
# \param[in] folder         Folder in vault for state transition
# \param[in] actor          Actor of the status transition
# \param[in] newVaultStatus New vault status
iiPostVaultStatusTransition(*folder, *actor, *newVaultStatus) {
	on (*newVaultStatus == SUBMITTED_FOR_PUBLICATION) {
	        iiVaultGetActionActor(*folder, *actor, *actionActor);
		iiAddActionLogRecord(*actionActor, *folder, "submitted for publication");
	}
	on (*newVaultStatus == APPROVED_FOR_PUBLICATION) {
	        iiVaultGetActionActor(*folder, *actor, *actionActor);
		iiAddActionLogRecord(*actionActor, *folder, "approved for publication");

		# Package is approved and can be published now.
		iiVaultRequestStatusTransition(*folder, PUBLISHED, *status, *statusInfo);
	}
	on (*newVaultStatus == PUBLISHED) {
		iiAddActionLogRecord("system", *folder, "published");
	}
	on (*newVaultStatus == DEPUBLISHED) {
	        iiVaultGetActionActor(*folder, *actor, *actionActor);
		iiAddActionLogRecord(*actionActor, *folder, "depublished");
	}
	on (true) {
		nop;
	}
}

# \brief iiVaultSubmit    Submit a folder in the vault for publication
# \param[in]  folder      Path of folder in vault to submit for publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
iiVaultSubmit(*folder, *confirmationVersion, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, SUBMITTED_FOR_PUBLICATION, *status, *statusInfo);
}

# \brief iiVaultApprove   Approve a folder in the vault for publication
# \param[in]  folder      Path of folder in vault to approve for publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
iiVaultApprove(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, APPROVED_FOR_PUBLICATION, *status, *statusInfo);
}

# \brief iiVaultCancel    Cancel a submission in the vault for publication
# \param[in]  folder      Path of folder in vault to cancel publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
iiVaultCancel(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, UNPUBLISHED, *status, *statusInfo);
}

# \brief iiVaultDepublish Depublish a folder in the vault
# \param[in]  folder      Path of folder in vault to depublish
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
iiVaultDepublish(*folder, *confirmationVersion, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, DEPUBLISHED, *status, *statusInfo);
}