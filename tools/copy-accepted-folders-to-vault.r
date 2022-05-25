#!/usr/bin/irule -F

copyToVault {
	# Copy research folder to vault.
	# This script is kept as dumb as possible.
	# All processing and error handling is done by rule_folder_secure
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", CRONJOB_PENDING, *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*folder = *row.COLL_NAME;
			# When rule_folder_secure fails continue with the other folders.
                        # *errorcode = '0';
                        # rule_folder_secure(*folder, *errorcode);
			# if (*errorcode == '0') {
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
