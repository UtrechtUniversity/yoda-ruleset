copyToVault {
	# Copy research folder to vault.
	# This script is kept as dumb as possible.
	# All processing and error handling is done by iiFolderSecure
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", CRONJOB_PENDING, *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*folder = *row.COLL_NAME;
			# When iiFolderSecure fails continue with the other folders.
			if (errorcode(iiFolderSecure(*folder)) == 0) {
				*cronjobState = UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_OK;
				msiString2KeyValPair(*cronjobState, *cronjobStateKvp);
				*err = errormsg(msiRemoveKeyValuePairsFromObj(*cronjobStateKvp, *folder, "-C"), *msg);
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQInp, *GenQOut);
}
input null
output ruleExecOut
