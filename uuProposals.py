# \file      uuProposal.py
# \brief     Functions to handle research proposals.
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import irods_types
from datetime import datetime
from genquery import (row_iterator, paged_iterator, AS_DICT, AS_LIST)


def uuMetaAdd(callback, objType, objName, attribute, value):
    keyValPair = callback.msiString2KeyValPair(attribute + "=" + value,
                                               irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiSetKeyValuePairsToObj(keyValPair, objName, objType)


def uuMetaAssociate(callback, objType, objName, attribute, value):
    keyValPair = callback.msiString2KeyValPair(attribute + "=" + value,
                                               irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiAssociateKeyValuePairsToObj(keyValPair, objName, objType)


# \brief Assign a research proposal to one or more DMC members for review
#
# \param[in] assignees          JSON-formatted array of DMC members
# \param[in] researchProposalId Unique identifier of the research proposal
#
def assignProposal(callback, assignees, researchProposalId):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Construct research proposal path
        proposalPath = ('/tempZone/home/datarequests-research/' +
                        researchProposalId + '/proposal.json')

        # Remove existing assignedForReview attributes (in case the list of
        # assignees is updated)
        callback.msi_rmw_avu("-d", proposalPath, "assignedForReview", "%", "%")

        # Set assignedForReview metadata on proposal
        for assignee in json.loads(assignees):
            uuMetaAdd(callback, "-d", proposalPath, "assignedForReview",
                      assignee)

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


# \brief Persist a research proposal to disk.
#
# \param[in] data    JSON-formatted contents of the research proposal.
#
def submitProposal(callback, data, rei):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Create collection
        zonePath = '/tempZone/home/datarequests-research/'
        timestamp = datetime.now().strftime('%s')
        collPath = zonePath + str(timestamp)
        callback.msiCollCreate(collPath, 1, 0)

        # Write proposal data as JSON to the created collection
        proposalPath = collPath + "/proposal.json"
        ret_val = callback.msiDataObjCreate(proposalPath, "", 0)
        fileDescriptor = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileDescriptor, data, 0)
        callback.msiDataObjClose(fileDescriptor, 0)

        # Set the proposal fields as AVUs on the proposal JSON file
        rule_args = [proposalPath, "-d", "root", data]
        setJsonToObj(rule_args, callback, rei)

        # Set the status metadata field of the proposal to "submitted"
        uuMetaAdd(callback, "-d", proposalPath, "status", "submitted")

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


# \brief Set the status of a submitted research proposal to "approved"
#
# \param[in] researchProposalId Unique identifier of the research proposal.
#
def approveProposal(callback, researchProposalId, currentUserId):
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if approving user owns the proposal. If so, do not allow
        # approving
        result = isProposalOwner(callback, researchProposalId, currentUserId)
        if result['isProposalOwner']:
            raise Exception()

        # Construct path to the collection of the proposal
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]
        proposalPath = ("/" + clientZone + "/home/datarequests-research/" +
                        researchProposalId + "/proposal.json")
        uuMetaAdd(callback, "-d", proposalPath, "status", "approved")
        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


# \brief Retrieve a research proposal.
#
# \param[in] researchProposalId Unique identifier of the research proposal.
#
# \return The JSON-formatted contents of the research proposal and the status
#         of the research proposal.
#
def getProposal(callback, researchProposalId):
    status = -1
    statusInfo = "Internal server error"

    # Set collection path and file path
    collPath = '/tempZone/home/datarequests-research/' + researchProposalId
    filePath = collPath + '/proposal.json'

    # Get the size of the proposal JSON file and the status of the proposal
    results = []
    rows = row_iterator(["DATA_SIZE", "META_DATA_ATTR_VALUE"],
                        "COLL_NAME = '%s' and DATA_NAME = '%s' and META_DATA_ATTR_NAME = 'status'"
                        % (collPath, 'proposal.json'),
                        AS_DICT, callback)
    for row in rows:
        dataSize = row['DATA_SIZE']
        proposalStatus = row['META_DATA_ATTR_VALUE']

    # Get the contents of the proposal JSON file
    try:
        ret_val = callback.msiDataObjOpen("objPath=%s" % filePath, 0)
        fileDescriptor = ret_val['arguments'][1]
        ret_val = callback.msiDataObjRead(fileDescriptor, dataSize,
                                          irods_types.BytesBuf())
        fileBuffer = ret_val['arguments'][2]
        callback.msiDataObjClose(fileDescriptor, 0)
        proposalJSON = ''.join(fileBuffer.buf)
        status = 0
        statusInfo = "OK"
    except:
        proposalStatus = ""
        proposalJSON = ""

    return {'proposalJSON': proposalJSON, 'proposalStatus': proposalStatus,
            'status': status, 'statusInfo': statusInfo}


# \brief Get the owner of a research proposal.
#
# \param[in] researchProposalId Unique identifier of the research proposal.
#
# \return The user ID of the owner of the research proposal.
#
def isProposalOwner(callback, researchProposalId, currentUserId):
    status = -1
    statusInfo = "Internal server error"
    isProposalOwner = True

    # Get user ID of proposal owner
    try:
        # Construct path to the collection of the proposal
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]
        collPath = ("/" + clientZone + "/home/datarequests-research/" +
                    researchProposalId)

        # Get list of user IDs with permissions on the proposal and the type of
        # permission they have
        rows = row_iterator(["DATA_ACCESS_USER_ID", "DATA_ACCESS_NAME"],
                            ("DATA_NAME = 'proposal.json' and COLL_NAME like "
                            + "'%s'" % collPath),
                            AS_DICT, callback)

        # Get the user ID with ownership permissions
        proposalOwnerUserId = []
        for row in rows:
            if row["DATA_ACCESS_NAME"] == "own":
                proposalOwnerUserId.append(row["DATA_ACCESS_USER_ID"])

        # Check if exactly 1 owner was found. If not, wipe proposalOwner list
        # and set error status code
        if len(proposalOwnerUserId) != 1:
            status = -2
            statusInfo = ("Not exactly 1 owner found. " +
                          "Something is probably wrong.")
            raise Exception()

        # We only have 1 owner. Set proposalOwner to this owner
        proposalOwnerUserId = proposalOwnerUserId[0]

        # Compare the proposal owner user ID to the user ID of the current user
        isProposalOwner = proposalOwnerUserId == currentUserId

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    # Return data
    return {'isProposalOwner': isProposalOwner, 'status': status,
            'statusInfo': statusInfo}

# \brief Retrieve descriptive information of a number of research proposals.
#        This is used to render a paginated table of research proposals.
#
# \param[in] limit  The number of proposals to return.
# \param[in] offset Offset used for table pagination.
#
# \return List of descriptive information about a number of research proposals.
#
def DRAFTgetProposals(callback, limit, offset):
    # Query iRODS to get a list of submitted proposals (i.e. subcollections
    # of the datarequests-research collection)
    path = '/tempZone/home/datarequests-research'
    fields = ["COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME",
              "META_DATA_ATTR_VALUE"]
    conditions = [callback.uucondition("COLL_PARENT_NAME", "=", path),
                  callback.uucondition("DATA_NAME", "=", "proposal.json")]
    orderby = "COLL_NAME"
    ascdesc = "asc"

    callback.uuPaginatedQuery(fields, conditions, orderby, ascdesc,
                              limit, offset, 0, 0, 0)


def uuSubmitProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitProposal(callback,
                                                             rule_args[0], rei)))

def uuIsProposalOwner(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isProposalOwner(callback,
                                                  rule_args[0], rule_args[1])))

def uuApproveProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(approveProposal(callback,
                                                  rule_args[0], rule_args[1])))


def uuAssignProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(assignProposal(callback,
                                                             rule_args[0], rule_args[1])))


def uuGetProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getProposal(callback,
                                                          rule_args[0])))


def DRAFTuuGetProposals(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getProposals(callback, rule_args[0], rule_args[1])))
