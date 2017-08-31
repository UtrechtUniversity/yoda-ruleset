# \file iiVault.r
# \brief Copy folders to the vault
#
# \copyright Copyright (c) 2017, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE


# \brief iiVaultStatus
# \param[in]  folder	    Path of folder
# \param[out] folderStatus  Current status of vault folder
iiVaultStatus(*folder, *vaultStatus) {
	*vaultStatusKey = IIVAULTSTATUSATTRNAME;
	*vaultStatus = UNPUBLISHED;
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *folder AND META_COLL_ATTR_NAME = *vaultStatusKey) {
		*vaultStatus = *row.META_COLL_ATTR_VALUE;
	}
}

# \brief iiPreVaultStatusTransition  Actions taken before status transition
# \param[in] folder            Path of vault folder
# \param[in] currentStatus     Current status of vault folder
# \param[in] newStatus         New status of vault folder
iiPreVaultStatusTransition(*folder, *currentVaultStatus, *newVaultStatus) {
	on (true) {
		nop;
	}

}

# \brief iiPostVaultStatusTransition   Processing after Status had changed
# \param[in] folder
# \param[in] actor
# \param[in] newStatus
iiPostVaultStatusTransition(*folder, *actor, *newVaultStatus) {
	on (*newVaultStatus == APPROVED_FOR_PUBLICATION) {
		iiAddActionLogRecord(*actor, *folder, "approve");
	}
	on (true) {
		nop;
	}
}

# \brief iiVaultSubmit    Submit a folder in the vault for publication
# \param[in]  folder        path of folder to submit
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultSubmit(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != UNPUBLISHED || *currentVaultStatus != REJECTED_FOR_PUBLICATION) {
		*status = "WrongStatus";
		*statusInfo = "Cannot submit folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ SUBMITTED_FOR_PUBLICATION;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, SUBMITTED_FOR_PUBLICATION, uuClientFullName, *allowed, *reason);
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
	}
}

# \brief iiVaultApprove    Approve a folder in the vault for publication
# \param[in]  folder        path of folder to approve
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultApprove(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != SUBMITTED_FOR_PUBLICATION) {
		*status = "WrongStatus";
		*statusInfo = "Cannot approve folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ APPROVED_FOR_PUBLICATION;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, APPROVED_FOR_PUBLICATION, uuClientFullName, *allowed, *reason);
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
	}
}

# \brief iiVaultReject    Reject a folder in the vault for publication
# \param[in]  folder        path of folder to reject
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultReject(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != SUBMITTED_FOR_PUBLICATION) {
		*status = "WrongStatus";
		*statusInfo = "Cannot reject folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ REJECTED_FOR_PUBLICATION;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, REJECTED_FOR_PUBLICATION, uuClientFullName, *allowed, *reason);
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
	}
}

# \brief iiVaultPublish     Publish a folder in the vault
# \param[in]  folder        path of folder to publish
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultPublish(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != APPROVED_FOR_PUBLICATION) {
		*status = "WrongStatus";
		*statusInfo = "Cannot publish folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ PUBLISHED;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, PUBLISHED, uuClientFullName, *allowed, *reason);
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
	}
}

# \brief iiVaultDepublish   Depublish a folder in the vault
# \param[in]  folder        path of folder to publish
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultDepublish(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != PUBLISHED) {
		*status = "WrongStatus";
		*statusInfo = "Cannot depublish folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*vaultStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ DEPUBLISHED;
	msiString2KeyValPair(*vaultStatusStr, *vaultStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*vaultStatusKvp, *folder, "-C"), *msg);
	if (*err < 0) {
		iiVaultStatus(*folder, *currentFolderStatus);
		iiCanTransitionVaultStatus(*folder, *currentVaultStatus, DEPUBLISHED, uuClientFullName, *allowed, *reason);
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
	}
}
