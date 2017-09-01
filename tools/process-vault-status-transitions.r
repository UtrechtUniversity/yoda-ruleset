processVaultActions {
	# Scan for any pending vault actions in the datamanager area
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);	
	msiAddConditionToGenQuery("DATA_NAME", "=", IIMETADATAXMLNAME, *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_action", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;
			
			if (*collName like regex "/[^/]+/home/datamanager-.*") {
				writeLine("stdout", "processVaultActions: *collName - *row");

			   	
				*err = errorcode(iiVaultProcessStatusTransition(*folder, *newFolderStatus, *actor, *status, *statusInfo));
				if (*err < 0) {
					writeLine("stdout", "iiVaultProcessStatusTransition: *err");
					*status = "InternalError";
					*statusInfo = "";
				}
				if (*status != "Success") {
					writeLine("stdout", "iiVaultProcessStatusTransition: *status - *statusInfo");
				} else {
					writeLine("stdout", "iiVaultProcessStatusTransition: Successfully processed *metadataXmlPath");
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
