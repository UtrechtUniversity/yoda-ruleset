# \file      uuProposals.r
# \brief     Functions to handle proposals (only methods that haven't been
#            rewritten in Python yet).
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Retrieve descriptive information of a number of research proposals.
#        This is used to render a paginated table of research proposals.
#
# \param[in] limit  The number of proposals to return.
# \param[in] offset Offset used for table pagination.
#
# \return List of descriptive information about a number of research proposals.
#
uuGetProposals(*limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", "status"));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}


# \brief Same as uuGetProposals, but with a different META_DATA_ATTR_NAME as
#        query condition and fewer return fields. This is a necessary hack,
#        because the iRODS query language does not have an OR operator
#
# \param[in] limit         The number of proposals to return.
# \param[in] offset        Offset used for table pagination.
# \param[in] attributeName The attribute whose value should be returned
#
# \return List of descriptive information about a number of research proposals.
#
uuGetProposalsAdditionalFields(*limit, *offset, *attributeName, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", *attributeName));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}

# \brief Request proposal metadata change
#
# \param[in]  proposalColl                  Path to collection of the proposal
# \param[in]  attributeName                 Name of attribute to change
# \param[in]  newAttributeValue             New value of attribute
# \param[in]  newAttributeValueArrayLength  If newAttributeVaue is an array,
#                                           specify length. Needed for parsing
#
requestProposalMetadataChange(*proposalColl, *attributeName,
                              *newAttributeValue, *newAttributeValueArrayLength,
                              *status, *statusInfo) {
        *status = -1;
        *statusInfo = "Internal server error";

        # Get full name of user requesting the metadata change (i.e. the actor)
        *actor = uuClientFullName;

        # Retrieve collection id
        foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *proposalColl
                AND DATA_NAME = 'proposal.json') {
                *collId = *row.COLL_ID;
        }

        # Set the path of the user group to which the proposal belongs.
        # Hardcoded for now as all proposals are stored in the same user group
        *actorGroupPath = '/tempZone/home/datarequests-research';

        # Construct key-value pair (the key specifies the collection on which
        # the metadata change should be applied; the value is a JSON array
        # consisting of the path to the proposal collection, the attribute name
        # the new attribute value and the actor)
        *json_str = "[]";
        *size = 0;
        msi_json_arrayops(*json_str, *proposalColl, "add", *size);
        msi_json_arrayops(*json_str, *attributeName, "add", *size);
        msi_json_arrayops(*json_str, *newAttributeValue, "add", *size);
        msi_json_arrayops(*json_str, *newAttributeValueArrayLength, "add", *size);
        msi_json_arrayops(*json_str, *actor, "add", *size);
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "proposal_action_" ++
                     *collId, *json_str);

        # Set the delayed rule on the actor group (to be picked up and
        # processed when adminProposalActions is called)
        *err = errormsg(msiSetKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"),
                        *msg);
        if (*err < 0) {
                *status = "Unrecoverable";
                *statusInfo = "*err - *msg";
                succeed;
        }

        # Add proposal action status to actor group
        *proposalStatus = UUORGMETADATAPREFIX ++
                             "proposal_status_action_" ++ "*collId=PENDING";
        msiString2KeyValPair(*proposalStatus, *kvp);
        *err = errormsg(msiSetKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"),
                                                 *msg);
        if (*err < 0) {
                *status = "Unrecoverable";
                *statusInfo = "*err - *msg";
                succeed;
        } else {
                *status = "Success";
                *statusInfo = "";
                succeed;
        }
}


# \brief Perform admin operations on the proposal
#
adminProposalActions() {
        msiExecCmd("admin-proposalactions.sh", uuClientFullName, "", "", 0,
                   *out);
}


# \brief Process proposal metadata change request
#
# \param[in] proposalColl                  Collection of the proposal whose
#                                          metadata should be changed
# \param[in] attributeName                 Name of metadata attribute to change
# \param[in] newAttributeValue             The new value of the metadata
#                                          attribute
# \param[in] newAttributeValueArrayLength  The length of the array in case
#                                          newAttributeValue is a JSON array
# \param[in] actor                         The user that has requested the
#                                          change
#
# \return                                  Status and statusInfo (reports the
#                                          success/failure of the processing)
#
uuProposalProcessMetadataChange(*proposalColl, *attributeName,
                                *newAttributeValue,
                                *newAttributeValueArrayLength, *actor,
                                *status, *statusInfo) {
        *status = "Unknown";
        *statusInfo = "An internal error has occurred";

        # Check if user is rodsadmin
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin") {
                writeLine("stdout", "uuProposalProcessMetadataChange: " ++
                          "Should only be called by a rodsadmin");
                fail;
        }

        # Construct file path of file whose metadata should be changed
        *filePath = *proposalColl ++ "/proposal.json";

        # Grant temporary write ACL
        msiSetACL("default", "admin:write", uuClientFullName, *filePath);

        # Not so elegant way to handle the special case of assigning a proposal
        # for review to one or more DMC members
        if (*attributeName == "assignedForReview") {

                # Check if proposal is already assigned. If so, remove
                # the current assignees
                *alreadyAssigned = false;
                foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE
                                COLL_NAME = *proposalColl AND
                                DATA_NAME = "proposal.json" AND
                                META_DATA_ATTR_NAME = *attributeName) {
                        *alreadyAssigned = true;
                }
                if (*alreadyAssigned) {
                        *err = msi_rmw_avu("-d", *filePath, "assignedForReview",
                                   "%", "%");
                }

                # Convert JSON array of assignees to list
                *assignees = list();
                for (*i = 0;
                     *i < int(*newAttributeValueArrayLength);
                     *i = *i + 1) {
                        *assignee = "";
                        msi_json_arrayops(*newAttributeValue, *assignee,
                                          "get", *i);
                        *assignees = cons(*assignee, *assignees);
                }

                # Set assignedForReview metadata on proposal
                foreach(*assignee in *assignees) {
                        *AttrValStr = *attributeName ++ "=" ++ *assignee;
                        msiString2KeyValPair(*AttrValStr, *Kvp);
                        *err = errormsg(msiAssociateKeyValuePairsToObj(*Kvp,
                                            *filePath, "-d"), *msg);
                        if (*err < 0) {
                                if (*err == -818000) {
                                        *status = "PermissionDenied";
                                        *statusInfo = "User is not " ++
                                                      "permitted to modify " ++
                                                      "this attribute";
                                } else {
                                        *status = "Unrecoverable";
                                        *statusInfo = "*err - *msg";
                                }
                        } else {
                                *status = "Success";
                                *statusInfo = "";
                        }
                }
        } else {
                # Check if requested change isn't already present
                *currentAttributeValue = "";
                foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE
                                COLL_NAME = *proposalColl AND
                                DATA_NAME = "proposal.json" AND
                                META_DATA_ATTR_NAME = *attributeName) {
                        *currentAttributeValue = *row.META_DATA_ATTR_VALUE;
                }
                # If it is, do not apply the requested change
                if (*currentAttributeValue == *newAttributeValue) {
                        *status = "Success";
                        *statusInfo = "";
                # If not, apply the request change
                } else {
                        *AttrValStr = *attributeName ++ "=" ++
                                      *newAttributeValue;
                        msiString2KeyValPair(*AttrValStr, *Kvp);
                        *err = errormsg(msiSetKeyValuePairsToObj(*Kvp,
                                            *filePath, "-d"), *msg);
                        if (*err < 0) {
                                if (*err == -818000) {
                                        *status = "PermissionDenied";
                                        *statusInfo = "User is not " ++
                                                      "permitted to modify " ++
                                                      "this attribute";
                                } else {
                                        *status = "Unrecoverable";
                                        *statusInfo = "*err - *msg";
                                }
                        } else {
                                *status = "Success";
                                *statusInfo = "";
                        }
                }
        }

        # Revoke temporary write ACL
        msiSetACL("default", "admin:null", uuClientFullName, *filePath);
}
