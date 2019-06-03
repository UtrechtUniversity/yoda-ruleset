processProposalActions() {
	# Scan for any pending proposal actions.
	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("COLL_NAME", "", *GenQInp);
	msiAddSelectFieldToGenQuery("META_COLL_ATTR_VALUE", "", *GenQInp);
	msiAddConditionToGenQuery("META_COLL_ATTR_NAME", "like", UUORGMETADATAPREFIX ++ "proposal_action_%", *GenQInp);

	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*collName = *row.COLL_NAME;

			# Check if proposal metadata change is requested in datarequests-research group
			if (*collName like regex "/[^/]+/home/datarequests-research.*") {

                                # Get arguments necessary for processing of metadata change
				*proposalColl  = "";
                                *attributeName = "";
				*action        = "";
                                *attributeValueArrayLength = "";
				*actor         = "";
				*err1 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *proposalColl, "get", 0));
				*err2 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *attributeName, "get", 1));
				*err3 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *action, "get", 2));
				*err4 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *attributeValueArrayLength, "get", 3));
				*err5 = errorcode(msi_json_arrayops(*row.META_COLL_ATTR_VALUE, *actor, "get", 4));

                                # If arguments cannot be read, skip processing this request
				if (*err1 < 0 || *err2 < 0 || *err3 < 0 || *err4 < 0) {
					writeLine("stdout", "Failed to process request on *collName");
				} else {
					# Retrieve collection id of proposal collection
					foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *proposalColl) {
						*collId = *row.COLL_ID;
					}

					# Check if proposal is currently pending for metadata change
					*pending = false;
					*proposalActionStatus = UUORGMETADATAPREFIX ++ "proposal_status_action_" ++ "*collId";
					foreach(*row in SELECT COLL_ID WHERE META_COLL_ATTR_NAME = *proposalActionStatus AND META_COLL_ATTR_VALUE = 'PENDING') {
						*pending = true;
					}


					# Perform metadata change if action is pending
					if (*pending) {
						*err = errorcode(uuProposalProcessMetadataChange(*proposalColl, *attributeName, *action, *attributeValueArrayLength, *actor, *status, *statusInfo));
						if (*err < 0) {
				                        writeLine("stdout", "uuProposalProcessMetadataChange: *err");
							*status = "InternalError";
							*statusInfo = "";
						}

						# Check if rods can modify metadata and grant temporary write ACL if necessary
						msiCheckAccess(*collName, "modify metadata", *modifyPermission);
						if (*modifyPermission == 0) {
							writeLine("stdout", "Granting write access to *collName");
							msiSetACL("default", "admin:write", uuClientFullName, *collName);
						}

                                                # Set proposal status action to FAIL if the metadata change was unsuccessful
						if (*status != "Success") {
							*json_str = "[]";
							*size = 0;
							msi_json_arrayops(*json_str, *proposalColl, "add", *size);
							msi_json_arrayops(*json_str, *attributeName, "add", *size);
							msi_json_arrayops(*json_str, *action, "add", *size);
							msi_json_arrayops(*json_str, *actor, "add", *size);
							msiString2KeyValPair("", *proposalActionKvp);
							msiAddKeyVal(*proposalActionKvp, UUORGMETADATAPREFIX ++ "proposal_action_" ++ *collId, *json_str);

							*proposalStatus = UUORGMETADATAPREFIX ++ "proposal_status_action_" ++ "*collId" ++ "=FAIL";
							msiString2KeyValPair(*proposalStatus, *proposalStatusKvp);

							*err = errormsg(msiRemoveKeyValuePairsFromObj(*proposalActionKvp, *collName, "-C"), *msg);
							msiSetKeyValuePairsToObj(*proposalStatusKvp, *collName, "-C");
							writeLine("stdout", "uuProposalProcessMetadataChange: *status - *statusInfo");
                                                # Remove the delayed rule (i.e. the proposal_action_*collId and
                                                # proposal_status_action_*collId attributes) if the metadata change was successful
						} else {
							*json_str = "[]";
							*size = 0;
							msi_json_arrayops(*json_str, *proposalColl, "add", *size);
							msi_json_arrayops(*json_str, *attributeName, "add", *size);
							msi_json_arrayops(*json_str, *action, "add", *size);
							msi_json_arrayops(*json_str, *actor, "add", *size);
							msiString2KeyValPair("", *proposalActionKvp);
							msiAddKeyVal(*proposalActionKvp, UUORGMETADATAPREFIX ++ "proposal_action_" ++ *collId, *json_str);

							*proposalStatus = UUORGMETADATAPREFIX ++ "proposal_status_action_" ++ "*collId" ++ "=PENDING";
							msiString2KeyValPair(*proposalStatus, *proposalStatusKvp);

							*err = errormsg(msiRemoveKeyValuePairsFromObj(*proposalActionKvp, *collName, "-C"), *msg);
							*err = errormsg(msiRemoveKeyValuePairsFromObj(*proposalStatusKvp, *collName, "-C"), *msg);

							writeLine("stdout", "uuProposalProcessMetadataChange: Successfully processed *action by *actor on *proposalColl");
						}

						# Remove the temporary write ACL.
						if (*modifyPermission == 0) {
							writeLine("stdout", "Revoking write access to *collName");
							msiSetACL("default", "admin:null", uuClientFullName, *collName);
						}
					}
				}
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
