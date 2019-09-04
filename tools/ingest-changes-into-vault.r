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
				*err = errorcode(iiIngestDatamanagerMetadataIntoVault(*metadataPath, *status, *statusInfo));
				if (*err < 0) {
					writeLine("stdout", "iiIngestDatamanagerMetadataIntoVault: *err");
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


	# Scan for vault packages with a pending publication update.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ2Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "cronjob_publication_update", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", CRONJOB_PENDING, *GenQ2Inp);

	msiExecGenQuery(*GenQ2Inp, *GenQ2Out);
	msiGetContInxFromGenQueryOut(*GenQ2Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ2Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
				*err = errorcode(iiProcessPublication(*collName, *status));
				if (*err < 0) {
					writeLine("stdout", "iiProcessPublication *collName returned errorcode *err");
				} else {
				        if (*status == "OK") {
                                           msiString2KeyValPair("", *publicationUpdateKvp);
                                           *publicationUpdate = UUORGMETADATAPREFIX ++ "cronjob_publication_update=" ++ CRONJOB_PENDING;
                                           msiString2KeyValPair(*publicationUpdate, *publicationUpdateKvp);
                                           *err = errormsg(msiRemoveKeyValuePairsFromObj(*publicationUpdateKvp, *collName, "-C"), *msg);
					}
					writeLine("stdout", "iiProcessPublication *collName returned with status: *status");
					if (*status == "Retry") {
						delay ("<PLUSET>60s</PLUSET>") {
							iiScheduledVaultActions();
						}
					}
				}
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQ2Inp, *GenQ2Out, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQ2Inp, *GenQ2Out);
}
input null
output ruleExecOut
