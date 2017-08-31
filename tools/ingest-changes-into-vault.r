ingestChangesIntoVault {
	# First scan for any pending changes in the datamanager area
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);	
	msiAddConditionToGenQuery("DATA_NAME", "=", IIMETADATAXMLNAME, *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_ingest", *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_VALUE", "=", "Pending", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;
			*metadataXmlPath = *row.COLL_NAME ++ "/" ++ IIMETADATAXMLNAME;
			
			if (*collName like regex "/[^/]+/home/datamanager-.*") {	
				*err = errorcode(iiIngestDatamanagerMetadataIntoVault(*metadataXmlPath, *status, *statusInfo));
				if (*err < 0) {
					writeLine("stdout", "iiIngestDatamanagerMetadataIntoVault: *err");
					*status = "InternalError";
					*statusInfo = "";
				}
				if (*status != "Success") {
					msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_ingest=*status%"
						     ++ UUORGMETADATAPREFIX ++ "vault_ingest_info=*statusInfo", *kvp);
					msiSetKeyValuePairsToObj(*kvp, *metadataXmlPath, "-d");
					writeLine("stdout", "iiIngestDatamanagerIntoVault: *status - *statusInfo");
				} else {
					writeLine("stdout", "iiIngestDatamanagerIntoVault: Successfully processed *metadataXmlPath");
				}
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}
input null
output ruleExecOut
