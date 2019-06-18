# \file      uuDatarequest.py
# \brief     Functions to handle data requests.
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import irods_types
from datetime import datetime


def uuMetaAdd(callback, objType, objName, attribute, value):
    keyValPair = callback.msiString2KeyValPair(attribute + "=" + value,
                                               irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiSetKeyValuePairsToObj(keyValPair, objName, objType)


# \brief Persist a data request to disk.
#
# \param[in] data       JSON-formatted contents of the data request.
# \param[in] proposalId Unique identifier of the research proposal.
#
def submitDatarequest(callback, data, rei):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Create collection
        zonePath = '/tempZone/home/datarequests-research/'
        timestamp = datetime.now().strftime('%s')
        collPath = zonePath + str(timestamp)
        callback.msiCollCreate(collPath, 1, 0)

        # Write data request data to disk
        filePath = collPath + '/' + 'datarequest.json'
        ret_val = callback.msiDataObjCreate(filePath, "", 0)
        fileDescriptor = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileDescriptor, data, 0)
        callback.msiDataObjClose(fileDescriptor, 0)

        # Set the proposal fields as AVUs on the proposal JSON file
        rule_args = [filePath, "-d", "root", data]
        setJsonToObj(rule_args, callback, rei)

        # Set the status metadata field to "submitted"
        uuMetaAdd(callback, "-d", filePath, "status", "submitted")

        # Set permissions for certain groups on the subcollection
        callback.msiSetACL("recursive", "write",
                           "datarequests-research-datamanagers", collPath)
        callback.msiSetACL("recursive", "write",
                           "datarequests-research-board-of-directors", collPath)

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


# \brief Retrieve a data request.
#
# \param[in] requestId Unique identifier of the data request.
#
def getDatarequest(callback, requestId):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Construct filename
        collName = '/tempZone/home/datarequests-research/' + requestId
        fileName = 'datarequest.json'
        filePath = collName + '/' + fileName

        # Get the size of the datarequest JSON file and the request's status
        results = []
        rows = row_iterator(["DATA_SIZE", "COLL_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s' AND " +
                             "META_DATA_ATTR_NAME = 'status'") % (collName,
                                                                  fileName),
                            AS_DICT,
                            callback)
        for row in rows:
            collName = row['COLL_NAME']
            dataSize = row['DATA_SIZE']
            requestStatus = row['META_DATA_ATTR_VALUE']

        # Get the contents of the datarequest JSON file
        ret_val = callback.msiDataObjOpen("objPath=%s" % filePath, 0)
        fileDescriptor = ret_val['arguments'][1]
        ret_val = callback.msiDataObjRead(fileDescriptor, dataSize,
                                          irods_types.BytesBuf())
        fileBuffer = ret_val['arguments'][2]
        callback.msiDataObjClose(fileDescriptor, 0)
        requestJSON = ''.join(fileBuffer.buf)

        status = 0
        statusInfo = "OK"
    except:
        requestJSON = ""
        requestStatus = ""

    return {'requestJSON': requestJSON,
            'requestStatus': requestStatus, 'status': status,
            'statusInfo': statusInfo}




# \brief Check if the invoking user is also the owner of a given data request.
#
# \param[in] requestId        Unique identifier of the data request.
# \param[in] currentUserName  Username of the user whose ownership is checked.
#
# \return A boolean specifying whether the user owns the data request.
#
def isRequestOwner(callback, requestId, currentUserName):
    status = -1
    statusInfo = "Internal server error"
    isRequestOwner = True

    # Get username of data request owner
    try:
        # Construct path to the collection of the datarequest
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]
        collPath = ("/" + clientZone + "/home/datarequests-research/" +
                    requestId)

        # Query iCAT for the username of the owner of the data request
        rows = row_iterator(["DATA_OWNER_NAME"],
                            ("DATA_NAME = 'datarequest.json' and COLL_NAME like "
                            + "'%s'" % collPath),
                            AS_DICT, callback)

        # Extract username from query results
        requestOwnerUserName = []
        for row in rows:
            requestOwnerUserName.append(row["DATA_OWNER_NAME"])

        # Check if exactly 1 owner was found. If not, wipe
        # requestOwnerUserName list and set error status code
        if len(requestOwnerUserName) != 1:
            status = -2
            statusInfo = ("Not exactly 1 owner found. " +
                          "Something is probably wrong.")
            raise Exception()

        # We only have 1 owner. Set requestOwnerUserName to this owner
        requestOwnerUserName = requestOwnerUserName[0]

        # Compare the request owner username to the username of the current
        # user to determine ownership
        isRequestOwner = requestOwnerUserName == currentUserName

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    # Return data
    return {'isRequestOwner': isRequestOwner, 'status': status,
            'statusInfo': statusInfo}


# \brief Assign a data request to one or more DMC members for review
#
# \param[in] assignees          JSON-formatted array of DMC members
# \param[in] requestId          Unique identifier of the data request
#
def assignRequest(callback, assignees, requestId):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Construct data request collection path
        requestColl = ('/tempZone/home/datarequests-research/' +
                        requestId)

        # Check if data request has already been assigned. If true, set status
        # code to failure and do not perform requested assignment
        results = []
        rows = row_iterator(["META_DATA_ATTR_VALUE"],
                        ("COLL_NAME = '%s' and DATA_NAME = '%s' and " +
                         "META_DATA_ATTR_NAME = 'status'")
                        % (requestColl, 'datarequest.json'),
                        AS_DICT, callback)
        for row in rows:
            requestStatus = row['META_DATA_ATTR_VALUE']
        if not requestStatus == "submitted":
            status = -1
            statusInfo = "Proposal is already assigned."
            raise Exception()

        # Assign the data request by adding a delayed rule that sets one or more
        # "assignedForReview" attributes on the datarequest (the number of
        # attributes is determined by the number of assignees) ...
        status = ""
        statusInfo = ""
        callback.requestDatarequestMetadataChange(requestColl,
                                                  "assignedForReview",
                                                  assignees,
                                                  str(len(
                                                      json.loads(assignees))),
                                                  status, statusInfo)

        # ... and triggering the processing of delayed rules
        callback.adminDatarequestActions()

        # Add and execute a delayed rule for setting the status to "assigned"
        status = ""
        statusInfo = ""
        callback.requestDatarequestMetadataChange(requestColl, "status",
                                                  "assigned", "", status,
                                                  statusInfo)
        callback.adminDatarequestActions()

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


# \brief Set the status of a submitted datarequest to "approved"
#
# \param[in] requestId        Unique identifier of the datarequest.
# \param[in] currentUserName  Username of the user whose ownership is checked.
#
def approveRequest(callback, requestId, currentUserName):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if approving user owns the datarequest. If so, do not allow
        # approving
        result = isRequestOwner(callback, requestId, currentUserName)
        if result['isRequestOwner']:
            raise Exception()

        # Construct path to the collection of the datarequest
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]
        requestColl = ("/" + clientZone + "/home/datarequests-research/" +
                        requestId)

        # Approve the datarequest by adding a delayed rule that sets the status
        # of the datarequest to "approved" ...
        status = ""
        statusInfo = ""
        callback.requestDatarequestMetadataChange(requestColl, "status",
                                               "approved", 0, status, statusInfo)

        # ... and triggering the processing of delayed rules
        callback.adminDatarequestActions()

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def uuAssignRequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(assignRequest(callback,
                                                            rule_args[0], rule_args[1])))


def uuApproveRequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(approveRequest(callback,
                                                  rule_args[0], rule_args[1])))


def uuIsRequestOwner(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isRequestOwner(callback,
                                                  rule_args[0], rule_args[1])))


def uuSubmitDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatarequest(callback,
                                                                rule_args[0], rei)))


def uuGetDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getDatarequest(callback,
                                                             rule_args[0])))
