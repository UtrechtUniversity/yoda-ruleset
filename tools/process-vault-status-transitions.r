processVaultActions {
	# Scan for any pending vault actions.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddSelectFieldToGenQuery("META_COLL_ATTR_VALUE", "", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "like", UUORGMETADATAPREFIX ++ "vault_action_", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;

`			# Check if vault status transition is requested in research or datamanager group.
			if (*collName like regex "/[^/]+/home/research-.*" ||
			    *collName like regex "/[^/]+/home/datamanager-.*") {
                               *folder = "";
                               *action = "";
                               *actor = "";
                               msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *folder, "get", 0);
                               msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *action, "get", 1);
                               msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actor, "get", 2);

			       # Retrieve collection id from folder.
			       foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *folder) {
			               *collId = *row.COLL_ID;
			       }

			       # Check if vault package is currently pending for status transition.
			       *pending = false;
			       *vaultActionStatus = UUORGMETADATAPREFIX ++ "vault_status_action_*coll_id";
			       foreach(*row in SELECT COLL_ID WHERE META_COLL_ATTR_NAME = *vaultActionStatus AND META_COLL_ATTR_VALUE = 'PENDING') {
			               *pending = true;
			       }

			       # Perform status transition if action is pending.
			       if (*pending) {
                                        *err = errorcode(iiVaultProcessStatusTransition(*folder, *action, *actor, *status, *statusInfo));
				        if (*err < 0) {
				               writeLine("stdout", "iiVaultProcessStatusTransition: *err");
					       *status = "InternalError";
					       *statusInfo = "";
				        }

				        if (*status != "Success") {
						*vaultAction = UUORGMETADATAPREFIX ++ "vault_action_" ++ "*collId" ++ "=" ++ *row.META_COLL_ATTR_VALUE;
						*vaultStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId" ++ "=FAIL";
						msiString2KeyValPair(*vaultAction, *vaultActionKvp);
						msiString2KeyValPair(*vaultStatus, *vaultStatusKvp);
						*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultActionKvp, *collName, "-C"), *msg);
						msiSetKeyValuePairsToObj(*vaultStatusKvp, *collName, "-C");
						writeLine("stdout", "iiVaultProcessStatusTransition: *status - *statusInfo");
				        } else {
					        *vaultAction = UUORGMETADATAPREFIX ++ "vault_action_" ++ "*collId" ++ "=" ++ *row.META_COLL_ATTR_VALUE;
						*vaultStatus = UUORGMETADATAPREFIX ++ "vault_status_action_" ++ "*collId" ++ "=PENDING";
						msiString2KeyValPair(*vaultAction, *vaultActionKvp);
						msiString2KeyValPair(*vaultStatus, *vaultStatusKvp);
						*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultActionKvp, *collName, "-C"), *msg);
						*err = errormsg(msiRemoveKeyValuePairsFromObj(*vaultStatusKvp, *collName, "-C"), *msg);
						writeLine("stdout", "iiVaultProcessStatusTransition: Successfully processed *action by *actor on *folder");
				        }
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
