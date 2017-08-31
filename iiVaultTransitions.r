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

# \brief iiVaultApprove    Approve a folder in the vault for publication
# \param[in]  folder        path of folder to approve
# \param[out] status        status of the action
# \param[out] statusInfo    Informative message when action was not successfull
iiVaultApprove(*folder, *status, *statusInfo) {
	*status = "Unknown";
	*statusInfo = "An internal error has occurred";

	iiVaultStatus(*folder, *currentVaultStatus);
	if (*currentVaultStatus != UNPUBLISHED) {
		*status = "WrongStatus";
		*statusInfo = "Cannot lock folder as it is currently in *currentVaultStatus state";
		succeed;
	}

	*folderStatusStr = IIVAULTSTATUSATTRNAME ++ "=" ++ APPROVED_FOR_PUBLICATION;
	msiString2KeyValPair(*folderStatusStr, *folderStatusKvp);
	*err = errormsg(msiSetKeyValuePairsToObj(*folderStatusKvp, *folder, "-C"), *msg);
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
