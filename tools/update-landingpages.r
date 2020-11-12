updateLandingpages() {
	# Scan for published vault packages.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ2Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_status", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", PUBLISHED, *GenQ2Inp);

	msiExecGenQuery(*GenQ2Inp, *GenQ2Out);
	msiGetContInxFromGenQueryOut(*GenQ2Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ2Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
                *status = ''
                *statusInfo = '';
				rule_update_landingpage(*collName, *status, *statusInfo);
                writeLine("stdout", "*status");
                writeLine("stdout", "*statusInfo");
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
