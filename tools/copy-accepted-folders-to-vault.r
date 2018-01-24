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
                        *collName = *row.COLL_NAME;

			# Check if vault package copy is requested in research or datamanager group.
			if (*collName like regex "/[^/]+/home/research-.*" ||
			    *collName like regex "/[^/]+/home/datamanager-.*") {

			       # Check if copy request is being processed.
			       *processing = false;
			       foreach(*row in SELECT COLL_NAME WHERE
			                COLL_NAME = *collName AND
			                META_COLL_ATTR_NAME = "org_cronjob_copy_to_research" AND
			                META_COLL_ATTR_VALUE = 'CRONJOB_PROCESSING') {
                                	*processing = true;
			       }
				
                               *folder = "";
                               *target = "";
                               *err1 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *folder, "get", 0));
                               *err2 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *target, "get", 1));

				if (*err1 < 0 || *err2 < 0) {
					writeLine("stdout", "Failed to process copy request on *collName,");
					*processing = false;
				}
				
				if (!*processing) {
                                   # When iiCopyFolderToResearch fails continue with the other folders.
                                   iiCopyFolderToResearch(*folder, *target) ::: nop;

                                   # Check if rods can modify metadata and grant temporary write ACL if necessary.
                                   msiCheckAccess(*collName, "modify metadata", *modifyPermission);
                                   if (*modifyPermission == 0) {
                                           writeLine("stdout", "Granting read access to *collName");
                                           msiSetACL("default", "admin:write", uuClientFullName, *collName);
                                   }

                                   # Remove copy request.
                                   *json_str = "[]";
                                   *size = 0;
                                   msi_json_arrayops(*json_str, *folder, "add", *size);
                                   msi_json_arrayops(*json_str, *target, "add", *size);
                                   msiString2KeyValPair("", *copyKvp);
                                   msiAddKeyVal(*copyKvp, UUORGMETADATAPREFIX ++ "copy_vault_package", *json_str);
                                   *err = errormsg(msiRemoveKeyValuePairsFromObj(*copyKvp, *collName, "-C"), *msg);

                                   # Remove cronjob status.
                                   *cronjobState = UUORGMETADATAPREFIX ++ "cronjob_copy_to_research=" ++ CRONJOB_OK;
                                   msiString2KeyValPair(*cronjobState, *cronjobStateKvp);
                                   *err = errormsg(msiRemoveKeyValuePairsFromObj(*cronjobStateKvp, *collName, "-C"), *msg);

                                   # Remove the temporary write ACL.
                                   if (*modifyPermission == 0) {
                                           writeLine("stdout", "Revoking read access to *collName");
                                           msiSetACL("default", "admin:null", uuClientFullName, *collName);
                                   }
			        }
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
