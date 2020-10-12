# \file      uuDatarequest.py
# \brief     Functions to handle data requests (only methods that have not been
#            rewritten in Python yet).
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Request data request metadata change
#
# \param[in]  requestColl                   Path to collection of the data
#                                           request
# \param[in]  attributeName                 Name of attribute to change
# \param[in]  newAttributeValue             New value of attribute
# \param[in]  newAttributeValueArrayLength  If newAttributeValue is a JSON
#                                           array, specify length. Needed for
#                                           parsing
#
requestDatarequestMetadataChange(*requestColl, *attributeName,
                                 *newAttributeValue, *newAttributeValueArrayLength,
                                 *status, *statusInfo) {
        # Set default status
        *status = -1;
        *statusInfo = "Internal server error";

        # Get full name of user requesting the metadata change (i.e. the actor)
        *actor = uuClientFullName;

        # Retrieve collection id
        foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *requestColl
                AND DATA_NAME = 'datarequest.json') {
                *collId = *row.COLL_ID;
        }

        # Set the path of the user group to which the data request belongs.
        # Hardcoded for now as all data requests are stored in the same user
        # group
        *actorGroupPath = '/tempZone/home/datarequests-research';

        # Construct key-value pair (the key specifies the collection on which
        # the metadata change should be applied; the value is a JSON array
        # consisting of the path to the data request collection, the attribute
        # name, the new attribute value and the actor)
        *json_str = "[]";
        *size = 0;
        msi_json_arrayops(*json_str, *requestColl, "add", *size);
        msi_json_arrayops(*json_str, *attributeName, "add", *size);
        msi_json_arrayops(*json_str, *newAttributeValue, "add", *size);
        msi_json_arrayops(*json_str, *newAttributeValueArrayLength, "add", *size);
        msi_json_arrayops(*json_str, *actor, "add", *size);
        msiString2KeyValPair("", *kvp);
        msiAddKeyVal(*kvp, UUORGMETADATAPREFIX ++ "datarequest_action_" ++
                     *collId, *json_str);

        # Set the delayed rule on the actor group (to be picked up and
        # processed when adminDatarequestActions is called)
        *err = errormsg(msiSetKeyValuePairsToObj(*kvp, *actorGroupPath, "-C"),
                        *msg);
        if (*err < 0) {
                *status = "Unrecoverable";
                *statusInfo = "*err - *msg";
                succeed;
        }

        # Add data request action status to actor group
        *requestStatus = UUORGMETADATAPREFIX ++
                             "datarequest_status_action_" ++ "*collId=PENDING";
        msiString2KeyValPair(*requestStatus, *kvp);
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


# \brief Perform admin operations on the data request
#
adminDatarequestActions() {
        msiExecCmd("admin-datarequestactions.sh", uuClientFullName, "", "", 0,
                   *out);
}


# \brief Process request to change data request metadata
#
# \param[in] requestColl                   Collection of the data request whose
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
uuDatarequestProcessMetadataChange(*datarequestColl, *attributeName,
                                *newAttributeValue,
                                *newAttributeValueArrayLength, *actor,
                                *status, *statusInfo) {
        # Set default status
        *status = "Unknown";
        *statusInfo = "An internal error has occurred";

        # Check if user is rodsadmin (this is required)
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin") {
                writeLine("stdout", "uuDatarequestProcessMetadataChange: " ++
                          "Should only be called by a rodsadmin");
                fail;
        }

        # Construct file path of file whose metadata should be changed
        *filePath = *datarequestColl ++ "/datarequest.json";

        # Grant temporary write ACL
        msiSetACL("default", "admin:write", uuClientFullName, *filePath);

        # Not so elegant way to handle the special case of assigning a data
        # request for review to one or more DMC members
        if (*attributeName == "assignedForReview") {

                # Check if data request is already assigned. If so, remove
                # the current assignees
                *alreadyAssigned = false;
                foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE
                                COLL_NAME = *datarequestColl AND
                                DATA_NAME = "datarequest.json" AND
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

                # Set assignedForReview metadata on the data request
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
                                COLL_NAME = *datarequestColl AND
                                DATA_NAME = "datarequest.json" AND
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
