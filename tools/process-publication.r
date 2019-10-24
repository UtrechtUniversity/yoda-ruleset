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
				*err = errorcode(iiProcessPublication(*collName, *status));
				if (*err < 0) {
					writeLine("stdout", "iiProcessPublication *collName returned errorcode *err");
				} else {
					writeLine("stdout", "iiProcessPublication *collName returned with status: *status");
				}
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
				*err = errorcode(iiProcessDepublication(*collName, *status));
				if (*err < 0) {
					writeLine("stdout", "iiProcessDepublication *collName returned errorcode *err");
				} else {
					writeLine("stdout", "iiProcessDepublication *collName returned with status: *status");
				}
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
				*err = errorcode(iiProcessRepublication(*collName, *status));
				if (*err < 0) {
					writeLine("stdout", "iiProcessRepublication *collName returned errorcode *err");
				} else {
					writeLine("stdout", "iiProcessRepublication *collName returned with status: *status");
				}
			}
		}

		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQ4Inp, *GenQ4Out, *ContInxNew);
		}
	}
	msiCloseGenQuery(*GenQ4Inp, *GenQ4Out);
}
input null
output ruleExecOut
