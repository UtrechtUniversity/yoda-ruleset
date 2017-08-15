moveDatamanagerMetadataIntoVault {
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);	
	msiAddConditionToGenQuery("DATA_NAME", "=", IIMETADATAXMLNAME, *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "move_to_vault", *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_VALUE", "=", "True", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;
			*metadataXmlPath = *row.COLL_NAME ++ "/" ++ IIMETADATAXMLNAME;
				
			iiIngestDatamanagerMetadataIntoVault(*metadataXmlPath) ::: nop;
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}
input null
output ruleExecOut
