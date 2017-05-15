copyToVault {
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);	
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", IISTATUSATTRNAME, *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", ACCEPTED, *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*folder = *row.COLL_NAME;
			msiCheckAccess(*folder, "modify object", *result);
			if (*result == 1) {
				iiCopyFolderToVault(*folder) ::: nop;
			} else {
				msiSetACL("recursive", "admin:write", uuClientFullName, *folder);
				iiCopyFolderToVault(*folder) ::: nop;
				msiSetACL("recursive", "admin:null", uuClientFullName, *folder);
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
