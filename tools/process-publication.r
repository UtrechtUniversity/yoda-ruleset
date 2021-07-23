processPublication() {
	# Scan for vault packages approved for publication .
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ2Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_status", *GenQ2Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", APPROVED_FOR_PUBLICATION, *GenQ2Inp);

	msiExecGenQuery(*GenQ2Inp, *GenQ2Out);
	msiGetContInxFromGenQueryOut(*GenQ2Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ2Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
                    *status = '';
                    *statusInfo = '';
                    rule_process_publication(*collName, *status, *statusInfo);
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

	# Scan for vault packages for which depublication is requested.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ3Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ3Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_status", *GenQ3Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", PENDING_DEPUBLICATION, *GenQ3Inp);

	msiExecGenQuery(*GenQ3Inp, *GenQ3Out);
	msiGetContInxFromGenQueryOut(*GenQ3Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ3Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
                    *status = ''
                    *statusInfo = '';
                    rule_process_depublication(*collName, *status, *statusInfo);
                    writeLine("stdout", "*status");
                    writeLine("stdout", "*statusInfo");
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQ3Inp, *GenQ3Out, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQ3Inp, *GenQ3Out);

	# Scan for vault packages for which republication is requested.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ4Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ4Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "vault_status", *GenQ4Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", PENDING_REPUBLICATION, *GenQ4Inp);

	msiExecGenQuery(*GenQ4Inp, *GenQ4Out);
	msiGetContInxFromGenQueryOut(*GenQ4Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ4Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
                    *status = ''
                    *statusInfo = '';
                    rule_process_republication(*collName, *status, *statusInfo);
                    writeLine("stdout", "*status");
                    writeLine("stdout", "*statusInfo");
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQ4Inp, *GenQ4Out, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQ4Inp, *GenQ4Out);

	# Scan for vault packages with a pending publication update.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQ5Inp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "%%/home/vault-%%", *GenQ5Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "cronjob_publication_update", *GenQ5Inp);
	msiAddConditionToGenQuery("META_COLL_ATTR_VALUE", "=", CRONJOB_PENDING, *GenQ5Inp);

	msiExecGenQuery(*GenQ5Inp, *GenQ5Out);
	msiGetContInxFromGenQueryOut(*GenQ5Out, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQ5Out) {
			*collName = *row.COLL_NAME;

			# Check if this really is a vault package
			if (*collName like regex "/[^/]+/home/vault-.*") {
                                       *status = '';
                                       *statusInfo = '';
                                       rule_update_publication(*collName, *status, *statusInfo);
                                       writeLine("stdout", "rule_update_publication *collName returned with status: *status");
                                       if (*status == "OK") {
                                           msiString2KeyValPair("", *publicationUpdateKvp);
                                           *publicationUpdate = UUORGMETADATAPREFIX ++ "cronjob_publication_update=" ++ CRONJOB_PENDING;
                                           msiString2KeyValPair(*publicationUpdate, *publicationUpdateKvp);
                                           *err = errormsg(msiRemoveKeyValuePairsFromObj(*publicationUpdateKvp, *collName, "-C"), *msg);
				}
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQ5Inp, *GenQ5Out, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQ5Inp, *GenQ5Out);
}
input null
output ruleExecOut
