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
			iiFolderSecure(*folder) ::: nop;

			*cronjobState = UUORGMETADATAPREFIX ++ "cronjob_copy_to_vault=" ++ CRONJOB_OK;
			msiString2KeyValPair(*cronjobState, *cronjobStateKvp);
			*err = errormsg(msiRemoveKeyValuePairsFromObj(*cronjobStateKvp, *folder, "-C"), *msg);
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}

        # Copy vault package to research area.
        # This script is kept as dumb as possible.
        # All processing and error handling is done by iiCopyFolderToResearch.
        *CopyContInxOld = 1;
        msiAddSelectFieldToGenQuery("COLL_NAME", "", *CopyGenQInp);
        msiAddSelectFieldToGenQuery("META_COLL_ATTR_VALUE", "", *CopyGenQInp);
        msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "copy_vault_package", *CopyGenQInp);
        msiExecGenQuery(*CopyGenQInp, *CopyGenQOut);
        msiGetContInxFromGenQueryOut(*CopyGenQOut, *CopyContInxNew);

        while(*CopyContInxOld > 0) {
                foreach(*row in *CopyGenQOut) {
                        *folder = *row.META_COLL_ATTR_VALUE;
                        *target = *row.COLL_NAME;
                        writeLine("stdout", "iiCopyFolderToResearch: Copying *folder to *target");

			# Check if copy request is being processed.
			foreach(*row in SELECT COLL_NAME WHERE
			                COLL_NAME = *target AND
			                META_COLL_ATTR_NAME = UUORGMETADATAPREFIX ++ "cronjob_copy_to_research" AND
			                META_COLL_ATTR_VALUE = 'CRONJOB_PROCESSING') {
                                *processing = true;
			}

			if (!*processing) {
                                # When iiCopyFolderToResearch fails continue with the other folders.
                                iiCopyFolderToResearch(*folder, *target) ::: nop;

                                # Remove copy request.
                                *copyRequest = UUORGMETADATAPREFIX ++ "copy_vault_package" ++ "=*folder";
                                msiString2KeyValPair(*copyRequest, *copyRequestKvp);
                                *err = errormsg(msiRemoveKeyValuePairsFromObj(*copyRequestKvp, *target, "-C"), *msg);

                                # Remove cronjob status.
                                *cronjobState = UUORGMETADATAPREFIX ++ "cronjob_copy_to_research=" ++ CRONJOB_OK;
                                msiString2KeyValPair(*cronjobState, *cronjobStateKvp);
                                *err = errormsg(msiRemoveKeyValuePairsFromObj(*cronjobStateKvp, *target, "-C"), *msg);
			}
                }

                *CopyContInxOld = *CopyContInxNew;
                if(*CopyContInxOld > 0) {
                        msiGetMoreRows(*CopyGenQInp, *CopyGenQOut, *CopyContInxNew);
                }
        }
}
input null
output ruleExecOut
