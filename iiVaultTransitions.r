# \file      iiVaultTransitions.r
# \brief     Status transitions for folders in the vault space.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Retrieve current vault folder status
#
# \param[in]  folder	    Path of vault folder
# \param[out] folderStatus  Current status of vault folder
#
iiVaultStatus(*folder, *vaultStatus) {
	*vaultStatusKey = IIVAULTSTATUSATTRNAME;
	*vaultStatus = UNPUBLISHED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *vaultStatusKey) {
		*vaultStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief Retrieve actor of action on vault folder
#
# \param[in]  folder      Path of action vault folder
# \param[out] actionActor Actor of action on vault folder
#
iiVaultGetActionActor(*folder, *actor, *actionActor) {
	# Retrieve vault folder collection id.
	foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
	        *collId = *row.COLL_ID;
	}

        # Retrieve vault folder action actor.
        *actionActor = "";
        foreach(*row in SELECT COLL_ID, META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = "org_vault_action_*collId") {
                *err = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actionActor, "get", 2));
                if (*err < 0) {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId contains invalid JSON");
                } else {
                        writeLine("serverLog", "iiVaultGetActionActor: org_vault_action_*collId actor is *actionActor");
                }
        }

        # Fallback actor (rodsadmin).
        if (*actionActor == "") {
                *actionActor = *actor;
        }
}


# \brief Request vault status transition action
#
# \param[in] folder
# \param[in] newFolderStatus
#
iiVaultRequestStatusTransition(*folder, *newVaultStatus, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		if (*newVaultStatus == PUBLISHED) {
			*status = "PermissionDenied";
			*statusInfo = "Vault status transition to published can only be requested by a rodsadmin.";
			succeed;
		} else if (*newVaultStatus == DEPUBLISHED) {
			*status = "PermissionDenied";
			*statusInfo = "Vault status transition to depublished can only be requested by a rodsadmin.";
			succeed;
		}
	}

	# Determine vault group and actor.
	*pathElems = split(*folder, "/");
	*rodsZone = elem(*pathElems, 0);
	*vaultGroup = elem(*pathElems, 2);
	*actor = uuClientFullName;

	# Retrieve user group name and user type.
	*actorGroup = "";
	rule_collection_group_name(*folder, *actorGroup);

	uuGroupGetMemberType(*actorGroup, uuClientFullName, *userType);

	# Check if user is datamanager.
	uuGroupGetCategory(*actorGroup, *category, *subcategory);
	uuGroupGetMemberType("datamanager-" ++ *category, uuClientFullName, *userTypeIfDatamanager);
	if (*userTypeIfDatamanager == "normal" || *userTypeIfDatamanager == "manager") {
		*isDatamanager = true;
	} else {
		*isDatamanager = false;
	}

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

	# Check if vault package is currently pending for status transition.
	# Except for status transition to PUBLISHED/DEPUBLISHED,
	# because it is requested by the system before previous pending
	# transition is removed.
	if (*newVaultStatus != PUBLISHED && *newVaultStatus != DEPUBLISHED) {
		*pending = false;
		*vaultActionStatus = UUORGMETADATAPREFIX ++ "vault_status_action_*collId";
		foreach(*row in SELECT COLL_ID WHERE META_COLL_ATTR_NAME = *vaultActionStatus AND META_COLL_ATTR_VALUE = 'PENDING') {
			*pending = true;
		}

		# Don't accept request if a status transition is already pending.
		if (*pending) {
			*status = "PermissionDenied";
			*statusInfo = "Vault package is being processed, please wait until finished.";
			succeed;
		}
	}

	# Check if status transition is allowed.
	iiVaultStatus(*folder, *currentVaultStatus);
	iiCanTransitionVaultStatus(*folder, *currentVaultStatus, *newVaultStatus, *actor, *allowed, *reason);
	if (!*allowed) {
		*status = "PermissionDenied";
		*statusInfo = *reason;
		succeed;
	}

	# Add vault action request to actor group.
	writeLine("serverLog", "iiVaultRequestStatusTransition: *newVaultStatus on *folder by *actor");
        *json_str = "[]";
        *size = 0;
        msi_json_arrayops(*json_str, *folder, "add", *size);
        msi_json_arrayops(*json_str, *newVaultStatus, "add", *size);
        msi_json_arrayops(*json_str, *actor, "add", *size);
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "vault_action_" ++ *collId, *json_str);
	*err = errormsg(msiAssociateKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"), *msg);
	if (*err < 0) {
		*status = "Unrecoverable";
		*statusInfo = "*err - *msg";
		succeed;
        }

	# Add vault action status to actor group.
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

# \brief Perform admin operations on the vault
#
iiAdminVaultActions() {
	msiExecCmd("admin-vaultactions.sh", uuClientFullName, "", "", 0, *out);
}

# \brief Processing vault status transition request
#
# \param[in] folder
# \param[in] newFolderStatus
# \param[in] actor
#
iiVaultProcessStatusTransition(*folder, *newFolderStatus, *actor, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		writeLine("stdout", "iiVaultStatusTransition: Should only be called by a rodsadmin");
		fail;
	}

	# Check if status isn't transitioned already.
        *currentVaultStatus = "";
        foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = IIVAULTSTATUSATTRNAME) {
                *currentVaultStatus = *row.META_COLL_ATTR_VALUE;
        }
        if (*currentVaultStatus == *newFolderStatus) {
                 *status = "Success";
                 *statusInfo = "";
                succeed;
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


# \brief Submit a folder in the vault for publication
#
# \param[in]  folder      Path of folder in vault to submit for publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
#
iiVaultSubmit(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, SUBMITTED_FOR_PUBLICATION, *status, *statusInfo);
	if (*status == "Success") {
		iiAdminVaultActions();
	}
}

# \brief Approve a folder in the vault for publication
#
# \param[in]  folder      Path of folder in vault to approve for publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
iiVaultApprove(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, APPROVED_FOR_PUBLICATION, *status, *statusInfo);
	if (*status == "Success") {
		iiAdminVaultActions();
	}
}

# \brief Cancel a submission in the vault for publication
#
# \param[in]  folder      Path of folder in vault to cancel publication
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
#
iiVaultCancel(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, UNPUBLISHED, *status, *statusInfo);
	if (*status == "Success") {
		iiAdminVaultActions();
	}
}

# \brief Depublish a folder in the vault
#
# \param[in]  folder      Path of folder in vault to depublish
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
#
iiVaultDepublish(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, PENDING_DEPUBLICATION, *status, *statusInfo);
	if (*status == "Success") {
		iiAdminVaultActions();
	}
}

# \brief Republish a folder in the vault
#
# \param[in]  folder      Path of folder in vault to republish
# \param[out] status      Status of the action
# \param[out] statusInfo  Informative message when action was not successful
#
iiVaultRepublish(*folder, *status, *statusInfo) {
	iiVaultRequestStatusTransition(*folder, PENDING_REPUBLICATION, *status, *statusInfo);
	if (*status == "Success") {
		iiAdminVaultActions();
	}
}
