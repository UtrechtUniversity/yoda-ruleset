processVaultActions() {
	# Scan for any pending vault actions.
	*ContInxOld = 1;

	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddSelectFieldToGenQuery("META_COLL_ATTR_VALUE", "", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "like", UUORGMETADATAPREFIX ++ "vault_action_%", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;
			# Check if vault status transition is requested in research or datamanager group.
			if (*collName like regex "/[^/]+/home/research-.*" ||
                            *collName like regex "/[^/]+/home/deposit-.*" ||
			    *collName like regex "/[^/]+/home/datamanager-.*") {

				*folder = "";
				*action = "";
				*actor = "";
				*err1 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *folder, "get", 0));
				*err2 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *action, "get", 1));
				*err3 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actor, "get", 2));

				if (*err1 < 0 || *err2 < 0 || *err3 < 0) {
					writeLine("stdout", "Failed to process vault request on *collName");
				} else { # skip processing this vault request
					# Retrieve collection id from folder.
					foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
						*collId = *row.COLL_ID;
					}

					# Check if vault package is currently pending for status transition.
					*pending = false;
					*vaultActionStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId";
					foreach(*row in SELECT COLL_ID WHERE META_COLL_ATTR_NAME = *vaultActionStatus AND META_COLL_ATTR_VALUE = 'PENDING') {
						*pending = true;
					}

					# Perform status transition if action is pending.
					if (*pending) {
                        *status = '';
                        *statusInfo = '';
                        rule_vault_process_status_transitions(*folder, *action, *actor, *status, *statusInfo);
                        *status = 'Success';

						# Check if rods can modify metadata and grant temporary write ACL if necessary.
						msiCheckAccess(*collName, "modify_metadata", *modifyPermission);
						if (*modifyPermission == 0) {
							writeLine("stdout", "Granting write access to *collName");
							msiSetACL("default", "admin:write", uuClientFullName, *collName);
						}

						if (*status != "Success") {
							*json_str = "[]";
							*size = 0;
							msi_json_arrayops(*json_str, *folder, "add", *size);
							msi_json_arrayops(*json_str, *action, "add", *size);
							msi_json_arrayops(*json_str, *actor, "add", *size);
							msiString2KeyValPair("", *vaultActionKvp);
							msiAddKeyVal(*vaultActionKvp, UUORGMETADATAPREFIX ++ "vault_action_" ++ *collId, *json_str);

							*vaultStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId" ++ "=FAIL";
							msiString2KeyValPair(*vaultStatus, *vaultStatusKvp);

							*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultActionKvp, *collName, "-C"), *msg);
							msiSetKeyValuePairsToObj(*vaultStatusKvp, *collName, "-C");
							writeLine("stdout", "rule_vault_process_status_transitions: *status - *statusInfo");
						} else {
							*json_str = "[]";
							*size = 0;
							msi_json_arrayops(*json_str, *folder, "add", *size);
							msi_json_arrayops(*json_str, *action, "add", *size);
							msi_json_arrayops(*json_str, *actor, "add", *size);
							msiString2KeyValPair("", *vaultActionKvp);
							msiAddKeyVal(*vaultActionKvp, UUORGMETADATAPREFIX ++ "vault_action_" ++ *collId, *json_str);

							*vaultStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId" ++ "=PENDING";
							msiString2KeyValPair(*vaultStatus, *vaultStatusKvp);

							*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultActionKvp, *collName, "-C"), *msg);
							*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultStatusKvp, *collName, "-C"), *msg);

							writeLine("stdout", "rule_vault_process_status_transitions: Successfully processed *action by *actor on *folder");
						}

						# Remove the temporary write ACL.
						if (*modifyPermission == 0) {
							writeLine("stdout", "Revoking write access to *collName");
							msiSetACL("default", "admin:null", uuClientFullName, *collName);
						}
					}
				} #/skip processing this vault request
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
