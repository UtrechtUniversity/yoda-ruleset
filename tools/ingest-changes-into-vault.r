ingestChangesIntoVault {
	# First scan for any pending changes in the datamanager area
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddConditionToGenQuery("DATA_NAME", "=", IIJSONMETADATA, *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "cronjob_vault_ingest", *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_VALUE", "=", CRONJOB_PENDING, *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;
			*metadataPath = *row.COLL_NAME ++ "/" ++ IIJSONMETADATA;

			if (*collName like regex "/[^/]+/home/datamanager-.*") {
				# ensure rodsadmin access to the datamanager collection and metadata
				*status     = "";
				*statusInfo = "";
				*err = errorcode(rule_meta_datamanager_vault_ingest(*metadataPath, *status, *statusInfo));
				if (*err < 0) {
					writeLine("stdout", "rule_meta_datamanager_vault_ingest: *err");
					*status = "InternalError";
					*statusInfo = "";
				}
				if (*status != "Success") {
					msiString2KeyValPair(UUORGMETADATAPREFIX ++ "cronjob_vault_ingest=CRONJOB_UNRECOVERABLE"
						     ++ UUORGMETADATAPREFIX ++ "cronjob_vault_ingest_info=*statusInfo", *kvp);
					*err = errorcode(msiSetKeyValuePairsToObj(*kvp, *metadataPath, "-d"));
					if (*err < 0) {
						writeLine("stdout", "iiIngestDatamanagerIntoVault: could not set error status on *metadataPath");
					}
					writeLine("stdout", "iiIngestDatamanagerIntoVault: *status - *statusInfo");
				} else {
					writeLine("stdout", "iiIngestDatamanagerIntoVault: Successfully processed *metadataPath");
				}
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
