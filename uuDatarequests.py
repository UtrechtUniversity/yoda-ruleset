# \file      uuDatarequest.py
# \brief     Functions to handle data requests.
# \author    Jelmer Zondergeld
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import irods_types
from datetime import datetime
from genquery import (row_iterator, AS_DICT)
from smtplib import SMTP
from email.mime.text import MIMEText


def sendMail(to, subject, body):
    """Send an email using the specified parameters.

       Arguments:
       to      -- Recipient email address
       subject -- Email message subject
       body    -- Email message body
    """
    # Construct message
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "test@example.org"
    msg["To"] = to

    # Send message
    #
    # TO-DO: fetch credentials (smtp_server_address, email_address,
    # password) from credential store
    # When testing, replace to with hardcoded email address
    s = SMTP('smtp_server_address')
    s.starttls()
    s.login("email_address", "password")
    s.sendmail("from_email_address", to, msg.as_string())
    s.quit()


def getGroupData(callback):
    """Return groups and related data.

       Copied from irods-ruleset-uu/uuGroup.py.
    """
    groups = {}

    # First query: obtain a list of groups with group attributes.
    ret_val = callback.msiMakeGenQuery(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            name = result.sqlResult[0].row(row)
            attr = result.sqlResult[1].row(row)
            value = result.sqlResult[2].row(row)

            # Create/update group with this information.
            try:
                group = groups[name]
            except Exception:
                group = {
                    "name": name,
                    "managers": [],
                    "members": [],
                    "read": []
                }
                groups[name] = group
            if attr in ["data_classification", "category", "subcategory"]:
                group[attr] = value
            elif attr == "description":
                # Deal with legacy use of '.' for empty description metadata.
                # See uuGroupGetDescription() in uuGroup.r for correct behavior of the old query interface.
                group[attr] = '' if value == '.' else value
            elif attr == "manager":
                group["managers"].append(value)

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    # Second query: obtain list of groups with memberships.
    ret_val = callback.msiMakeGenQuery(
        "USER_GROUP_NAME, USER_NAME, USER_ZONE",
        "USER_TYPE != 'rodsgroup'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            name = result.sqlResult[0].row(row)
            user = result.sqlResult[1].row(row)
            zone = result.sqlResult[2].row(row)

            if name != user and name != "rodsadmin" and name != "public":
                user = user + "#" + zone
                if name.startswith("read-"):
                    # Match read-* group with research-* or initial-* group.
                    name = name[5:]
                    try:
                        # Attempt to add to read list of research group.
                        group = groups["research-" + name]
                        group["read"].append(user)
                    except Exception:
                        try:
                            # Attempt to add to read list of initial group.
                            group = groups["initial-" + name]
                            group["read"].append(user)
                        except Exception:
                            pass
                elif not name.startswith("vault-"):
                    # Ardinary group.
                    group = groups[name]
                    group["members"].append(user)

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    return groups.values()


def groupUserMember(group, user, callback):
    """Check if a user is a member of the given group.

       Arguments:
       group -- Name of group
       user  -- Name of user
    """
    groups = getGroupData(callback)
    groups = list(filter(lambda grp: group == grp["name"] and
                         user in grp["members"], groups))

    return "true" if len(groups) == 1 else "false"


def setStatus(callback, requestId, status):
    """Set the status of a data request

       Arguments:
       requestId -- Unique identifier of the data request.
       status    -- The status to which the data request should be set.
    """

    # Construct path to the collection of the datarequest
    zoneName = ""
    clientZone = callback.uuClientZone(zoneName)['arguments'][0]
    requestColl = ("/" + clientZone + "/home/datarequests-research/" +
                   requestId)

    # Add delayed rule to update datarequest status
    responseStatus = ""
    responseStatusInfo = ""
    callback.requestDatarequestMetadataChange(requestColl, "status",
                                              status, 0, responseStatus,
                                              responseStatusInfo)

    # Trigger the processing of delayed rules
    callback.adminDatarequestActions()


def submitDatarequest(callback, data, rei):
    """Persist a data request to disk.

       Arguments:
       data -- JSON-formatted contents of the data request.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Create collection
        zonePath = '/tempZone/home/datarequests-research/'
        timestamp = datetime.now()
        requestId = str(timestamp.strftime('%s'))
        collPath = zonePath + requestId
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

        # Set permissions for certain groups on the subcollection
        callback.msiSetACL("recursive", "write",
                           "datarequests-research-datamanagers", collPath)
        callback.msiSetACL("recursive", "write",
                           "datarequests-research-data-management-committee",
                           collPath)
        callback.msiSetACL("recursive", "write",
                           "datarequests-research-board-of-directors", collPath)

        # Set the status metadata field to "submitted"
        setStatus(callback, requestId, "submitted")

        # Get parameters needed for sending emails
        researcherName = ""
        researcherEmail = ""
        researcherInstitute = ""
        researcherDepartment = ""
        proposalTitle = ""
        submissionDate = timestamp.strftime('%c')
        datamanagerEmails = ""
        rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s'") % (collPath,
                                                    'datarequest.json'),
                            AS_DICT,
                            callback)
        for row in rows:
            name = row["META_DATA_ATTR_NAME"]
            value = row["META_DATA_ATTR_VALUE"]
            if name == "name":
                researcherName = value
            elif name == "email":
                researcherEmail = value
            elif name == "institution":
                researcherInstitute = value
            elif name == "department":
                researcherDepartment = value
            elif name == "title":
                proposalTitle = value
        datamanagerEmails = json.loads(callback.uuGroupGetMembersAsJson(
                                       'datarequests-research-datamanagers',
                                       datamanagerEmails)['arguments'][1])

        # Send email to researcher and data manager notifying them of the
        # submission of this data request
        sendMail(researcherEmail, "[researcher] YOUth data request %s: submitted" % requestId, "Dear %s,\n\nYour data request has been submitted.\n\nYou will be notified by email of the status of your request. You may also log into Yoda to view the status and other information about your data request.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
        for datamanagerEmail in datamanagerEmails:
            if not datamanagerEmail == "rods":
                sendMail(datamanagerEmail, "[data manager] YOUth data request %s: submitted" % requestId, "Dear data manager,\n\nA new data request has been submitted.\n\nSubmitted by: %s (%s)\nAffiliation: %s, %s\nDate: %s\nRequest ID: %s\nProposal title: %s\n\nThe following link will take you to the detail page of the data request: https://portal.yoda.test/datarequest/view/%s.\n\nPlease review it carefully and assign it for review to the Data Management Committee using the \"Assign request\" button.\n\nWith kind regards,\nYOUth" % (researcherName, researcherEmail, researcherInstitute, researcherDepartment, submissionDate, requestId, proposalTitle, requestId))

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def getDatarequest(callback, requestId):
    """Retrieve a data request.

       Arguments:
       requestId -- Unique identifier of the data request.
    """
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


def isRequestOwner(callback, requestId, currentUserName):
    """Check if the invoking user is also the owner of a given data request.

       Arguments:
       requestId       -- Unique identifier of the data request.
       currentUserName -- Username of the user whose ownership is checked.

       Return:
       dict -- A JSON dict specifying whether the user owns the data request.
    """
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


def isReviewer(callback, requestId, currentUsername):
    """Check if the invoking user is assigned as reviewer to the given data request.

       Arguments:
       requestId       -- Unique identifier of the data request.
       currentUserName -- Username of the user that is to be checked.

       Return:
       dict -- A JSON dict specifying whether the user is assigned as reviewer to the data request.
    """
    status = -1
    statusInfo = "Internal server error"
    isReviewer = False

    try:
        # Reviewers are stored in one or more assignedForReview attributes on
        # the data request, so our first step is to query the metadata of our
        # data request file for these attributes

        # Declare variables needed for retrieving the list of reviewers
        collName = '/tempZone/home/datarequests-research/' + requestId
        fileName = 'datarequest.json'
        reviewers = []

        # Retrieve list of reviewers
        rows = row_iterator(["META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s' AND " +
                             "META_DATA_ATTR_NAME = 'assignedForReview'") % (collName,
                                                                             fileName),
                            AS_DICT,
                            callback)
        for row in rows:
            reviewers.append(row['META_DATA_ATTR_VALUE'])

        # Check if the reviewers list contains the current user
        isReviewer = currentUsername in reviewers

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    # Return the isReviewer boolean
    return {"isReviewer": isReviewer, "status": status,
            "statusInfo": statusInfo}


def assignRequest(callback, assignees, requestId):
    """Assign a data request to one or more DMC members for review.

       Arguments:
       assignees -- JSON-formatted array of DMC members.
       requestId -- Unique identifier of the data request

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if user is a data manager. If not, do not the user to assign the
        # request
        isDatamanager = False
        name = ""
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)
        if not isDatamanager:
            status = -2
            statusInfo = "User is not a data manager."
            raise Exception()

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
        setStatus(callback, requestId, "assigned")

        # Get parameters required for sending emails
        assigneeEmails = []
        researcherName = ""
        researcherEmail = ""
        proposalTitle = ""
        rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s'") % (requestColl,
                                                    'datarequest.json'),
                            AS_DICT,
                            callback)
        for row in rows:
            name = row["META_DATA_ATTR_NAME"]
            value = row["META_DATA_ATTR_VALUE"]
            if name == "name":
                researcherName = value
            elif name == "email":
                researcherEmail = value
            elif name == "title":
                proposalTitle = value
            elif name == "assignedForReview":
                assigneeEmails.append(value)

        # Send emails to the researcher and to the assignees
        sendMail(researcherEmail, "[researcher] YOUth data request %s: assigned" % requestId, "Dear %s,\n\nYour data request has been assigned for review by the YOUth data manager.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
        for assigneeEmail in assigneeEmails:
            sendMail(assigneeEmail, "[assignee] YOUth data request %s: assigned" % requestId, "Dear DMC member,\n\nData request %s (proposal title: \"%s\") has been assigned to you for review. Please sign in to Yoda to view the data request and submit your review.\n\nThe following link will take you directly to the review form: https://portal.yoda.test/datarequest/review/%s.\n\nWith kind regards,\nYOUth" % (requestId, proposalTitle, requestId))

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def submitReview(callback, data, requestId, rei):
    """Persist a data request review to disk.

       Arguments:
       data -- JSON-formatted contents of the data request review
       proposalId -- Unique identifier of the research proposal

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if user is a member of the Data Management Committee. If not, do
        # not allow submission of the review
        isDmcMember = False
        name = ""
        isDmcMember = groupUserMember("datarequests-research-data-management-committee",
                                      callback.uuClientFullNameWrapper(name)
                                      ['arguments'][0], callback)
        if not isDmcMember:
            status = -2
            statusInfo = "User is not a member of the Data Management Committee."
            raise Exception()

        # Check if the user has been assigned as a reviewer. If not, do not
        # allow submission of the review
        name = ""
        username = callback.uuClientNameWrapper(name)['arguments'][0]

        if not isReviewer(callback, requestId, username)['isReviewer']:
            status = -3
            statusInfo = "User is not assigned as a reviewer to this request."
            raise Exception()

        # Construct path to collection of review
        zonePath = '/tempZone/home/datarequests-research/'
        collPath = zonePath + requestId

        # Get username
        name = ""
        clientName = callback.uuClientNameWrapper(name)['arguments'][0]

        # Write review data to disk
        reviewPath = collPath + '/review_' + clientName + '.json'
        ret_val = callback.msiDataObjCreate(reviewPath, "", 0)
        fileDescriptor = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileDescriptor, data, 0)
        callback.msiDataObjClose(fileDescriptor, 0)

        # Give read permission on the review to Board of Director members
        callback.msiSetACL("default", "read",
                           "datarequests-research-board-of-directors",
                           reviewPath)

        # Remove the assignedForReview attribute of this user by first fetching
        # the list of reviewers ...
        collName = '/tempZone/home/datarequests-research/' + requestId
        fileName = 'datarequest.json'
        reviewers = []
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]

        ret_val = callback.msiMakeGenQuery(
            "META_DATA_ATTR_VALUE",
            (("COLL_NAME = '%s' AND DATA_NAME = 'datarequest.json' AND " +
             "META_DATA_ATTR_NAME = 'assignedForReview'") %
             (collName)).format(clientZone),
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]
        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        while True:
            result = ret_val["arguments"][1]
            for row in range(result.rowCnt):
                reviewers.append(result.sqlResult[0].row(row))

            if result.continueInx == 0:
                break
            ret_val = callback.msiGetMoreRows(query, result, 0)
        callback.msiCloseGenQuery(query, result)

        # ... then removing the current reviewer from the list
        reviewers.remove(clientName)

        # ... and then updating the assignedForReview attributes
        status = ""
        statusInfo = ""
        callback.requestDatarequestMetadataChange(collName,
                                                  "assignedForReview",
                                                  json.dumps(reviewers),
                                                  str(len(
                                                      reviewers)),
                                                  status, statusInfo)
        callback.adminDatarequestActions()

        # If there are no reviewers left, change the status of the proposal to
        # 'reviewed' and send an email to the board of directors members
        # informing them that the proposal is ready to be evaluated by them.
        if len(reviewers) < 1:
            setStatus(callback, requestId, "reviewed")

            # Get parameters needed for sending emails
            researcherName = ""
            researcherEmail = ""
            bodmemberEmails = ""
            rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                                ("COLL_NAME = '%s' AND " +
                                 "DATA_NAME = '%s'") % (collPath,
                                                        'datarequest.json'),
                                AS_DICT,
                                callback)
            for row in rows:
                name = row["META_DATA_ATTR_NAME"]
                value = row["META_DATA_ATTR_VALUE"]
                if name == "name":
                    researcherName = value
                elif name == "email":
                    researcherEmail = value

            bodmemberEmails = json.loads(callback.uuGroupGetMembersAsJson(
                                             'datarequests-research-board-of-directors',
                                             bodmemberEmails)['arguments'][1])

            # Send email to researcher and data manager notifying them of the
            # submission of this data request
            sendMail(researcherEmail, "[researcher] YOUth data request %s: reviewed" % requestId, "Dear %s,\n\nYour data request been reviewed by the YOUth data management committee and is awaiting final evaluation by the YOUth Board of Directors.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
            for bodmemberEmail in bodmemberEmails:
                if not bodmemberEmail == "rods":
                    sendMail(bodmemberEmail, "[bod member] YOUth data request %s: reviewed" %requestId, "Dear Board of Directors member,\n\nData request %s has been reviewed by the YOUth data management committee and is awaiting your final evaluation.\n\nPlease log into Yoda to evaluate the data request.\n\nThe following link will take you directly to the evaluation form: https://portal.yoda.test/datarequest/evaluate/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def getReview(callback, requestId):
    """Retrieve a data request review.

       Arguments:
       requestId -- Unique identifier of the data request
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Construct filename
        collName = '/tempZone/home/datarequests-research/' + requestId
        fileName = 'review_dmcmember.json'

        # Get the size of the review JSON file and the review's status
        results = []
        rows = row_iterator(["DATA_SIZE", "DATA_NAME", "COLL_NAME"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME like '%s'") % (collName, fileName),
                            AS_DICT,
                            callback)
        for row in rows:
            collName = row['COLL_NAME']
            dataName = row['DATA_NAME']
            dataSize = row['DATA_SIZE']

        # Construct path to file
        filePath = collName + '/' + dataName

        # Get the contents of the review JSON file
        ret_val = callback.msiDataObjOpen("objPath=%s" % filePath, 0)
        fileDescriptor = ret_val['arguments'][1]
        ret_val = callback.msiDataObjRead(fileDescriptor, dataSize,
                                          irods_types.BytesBuf())
        fileBuffer = ret_val['arguments'][2]
        callback.msiDataObjClose(fileDescriptor, 0)
        reviewJSON = ''.join(fileBuffer.buf)

        status = 0
        statusInfo = "OK"
    except:
        reviewJSON = ""

    return {'reviewJSON': reviewJSON, 'status': status,
            'statusInfo': statusInfo}


def submitEvaluation(callback, data, requestId, rei):
    """Persist an evaluation to disk.

       Arguments:
       data       -- JSON-formatted contents of the evaluation
       proposalId -- Unique identifier of the research proposal
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if user is a member of the Board of Directors. If not, do not
        # allow submission of the evaluation
        isBoardMember = False
        name = ""
        isBoardMember = groupUserMember("datarequests-research-board-of-directors",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)
        if not isBoardMember:
            status = -2
            statusInfo = "User is not a member of the Board of Directors."
            raise Exception()

        # Construct path to collection of the evaluation
        zonePath = '/tempZone/home/datarequests-research/'
        collPath = zonePath + requestId

        # Get username
        name = ""
        clientName = callback.uuClientNameWrapper(name)['arguments'][0]

        # Write evaluation data to disk
        reviewPath = collPath + '/evaluation_' + clientName + '.json'
        ret_val = callback.msiDataObjCreate(reviewPath, "", 0)
        fileDescriptor = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileDescriptor, data, 0)
        callback.msiDataObjClose(fileDescriptor, 0)

        # Update the status of the data request to "approved"
        setStatus(callback, requestId, "approved")

        # Get parameters needed for sending emails
        researcherName = ""
        researcherEmail = ""
        datamanagerEmails = ""
        rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s'") % (collPath,
                                                    'datarequest.json'),
                            AS_DICT,
                            callback)
        for row in rows:
            name = row["META_DATA_ATTR_NAME"]
            value = row["META_DATA_ATTR_VALUE"]
            if name == "name":
                researcherName = value
            elif name == "email":
                researcherEmail = value
        datamanagerEmails = json.loads(callback.uuGroupGetMembersAsJson('datarequests-research-datamanagers', datamanagerEmails)['arguments'][1])

        # Send an email to the researcher informing them of whether their data
        # request has been approved or rejected.
        evaluation = "approved"
        if evaluation == "approved":
            sendMail(researcherEmail, "[researcher] YOUth data request %s: approved" % requestId, "Dear %s,\n\nCongratulations! Your data request has been approved. The YOUth data manager will now create a Data Transfer Agreement for you to sign. You will be notified when it is ready.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
            for datamanagerEmail in datamanagerEmails:
                if not datamanagerEmail == "rods":
                    sendMail("j.j.zondergeld@uu.nl", "[data manager] YOUth data request %s: approved" % requestId, "Dear data manager,\n\nData request %s has been approved by the Board of Directors. Please sign in to Yoda to upload a Data Transfer Agreement for the researcher.\n\nThe following link will take you directly to the data request: https://portal.yoda.test/view/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))
        elif evaluation == "rejected":
            sendMail(researcherEmail, "[researcher] YOUth data request %s: rejected" % requestId, "Dear %s,\n\nYour data request has been rejected. Please log in to Yoda to view additional details.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nIf you wish to object against this rejection, please contact the YOUth data manager (%s).\n\nWith kind regards,\nYOUth" % (researcherName, requestId, datamanagerEmail[0]))

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def DTAGrantReadPermissions(callback, requestId, username, rei):
    """Grant read permissions on the DTA to the owner of the associated data request.

       Arguments:
       requestId --
       username  --
    """
    status = -1
    status = "Internal server error."

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
        requestOwnerUsername = []
        for row in rows:
            requestOwnerUsername.append(row["DATA_OWNER_NAME"])

        # Check if exactly 1 owner was found. If not, wipe
        # requestOwnerUserName list and set error status code
        if len(requestOwnerUsername) != 1:
            status = -2
            statusInfo = ("Not exactly 1 owner found. " +
                          "Something is probably wrong.")
            raise Exception()

        requestOwnerUsername = requestOwnerUsername[0]

        callback.msiSetACL("default", "read", requestOwnerUsername, collPath + "/dta.pdf")

        # Get parameters needed for sending emails
        researcherName = ""
        researcherEmail = ""
        rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s'") % (collPath,
                                                    'datarequest.json'),
                            AS_DICT,
                            callback)
        for row in rows:
            name = row["META_DATA_ATTR_NAME"]
            value = row["META_DATA_ATTR_VALUE"]
            if name == "name":
                researcherName = value
            elif name == "email":
                researcherEmail = value

        # Send an email to the researcher informing them that the DTA of their
        # data request is ready for them to sign and upload
        sendMail(researcherEmail, "[researcher] YOUth data request %s: DTA ready" % requestId, "Dear %s,\n\nThe YOUth data manager has created a Data Transfer Agreement to formalize the transfer of the data you have requested. Please sign in to Yoda to download and read the Data Transfer Agreement.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nIf you do not object to the agreement, please upload a signed copy of the agreement. After this, the YOUth data manager will prepare the requested data and will provide you with instructions on how to download them.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))

        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def requestDTAReady(callback, requestId, currentUserName):
    """Set the status of a submitted datarequest to "DTA ready".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose ownership is checked.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if the user requesting the status transition is a data manager.
        # If not, do not allow status transition
        isDatamanager = False
        name = ""
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)
        if not isDatamanager:
            status = -2
            statusInfo = "User is not a data manager."
            raise Exception()

        setStatus(callback, requestId, "dta_ready")

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def signedDTAGrantReadPermissions(callback, requestId, username, rei):
    """Grant read permissions on the signed DTA to the datamanagers group.

       Arguments:
       requestId -- Unique identifier of the datarequest.
       username  --
    """
    status = -1
    status = "Internal server error."

    try:
        # Construct path to the collection of the datarequest
        zoneName = ""
        clientZone = callback.uuClientZone(zoneName)['arguments'][0]
        collPath = ("/" + clientZone + "/home/datarequests-research/" +
                    requestId)

        callback.msiSetACL("default", "read",
                           "datarequests-research-datamanagers",
                           collPath + "/signed_dta.pdf")

        status = 0
        statusInfo = "OK"

        # Get parameters needed for sending emails
        datamanagerEmails = ""
        datamanagerEmails = json.loads(callback.uuGroupGetMembersAsJson('datarequests-research-datamanagers', datamanagerEmails)['arguments'][1])

        # Send an email to the data manager informing them that the DTA has been
        # signed by the researcher
        for datamanagerEmail in datamanagerEmails:
            if not datamanagerEmail == "rods":
                sendMail(datamanagerEmail, "[data manager] YOUth data request %s: DTA signed" % requestId, "Dear data manager,\n\nThe researcher has uploaded a signed copy of the Data Transfer Agreement for data request %s.\n\nPlease log in to Yoda to review this copy. The following link will take you directly to the data request: https://portal.yoda.test/datarequest/view/%s.\n\nAfter verifying that the document has been signed correctly, you may prepare the data for download. When the data is ready for the researcher to download, please click the \"Data ready\" button. This will notify the researcher by email that the requested data is ready. The email will include instructions on downloading the data.\n\nWith kind regards,\nYOUth" % (requestId, requestId))

    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def requestDTASigned(callback, requestId, currentUserName):
    """Set the status of a data request to "DTA signed".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose role is checked.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if uploading user owns the datarequest and only allow uploading
        # if this is the case
        result = isRequestOwner(callback, requestId, currentUserName)
        if not result['isRequestOwner']:
            raise Exception()

        setStatus(callback, requestId, "dta_signed")

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def requestDataReady(callback, requestId, currentUserName):
    """Set the status of a submitted datarequest to "Data ready".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose ownership is checked.
    """
    status = -1
    statusInfo = "Internal server error"

    try:
        # Check if the user requesting the status transition is a data manager.
        # If not, do not allow status transition
        isDatamanager = False
        name = ""
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)
        if not isDatamanager:
            status = -2
            statusInfo = "User is not a data manager."
            raise Exception()

        setStatus(callback, requestId, "data_ready")

        # Get parameters needed for sending emails
        researcherName = ""
        researcherEmail = ""
        rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND " +
                             "DATA_NAME = '%s'") % (requestColl,
                                                    'datarequest.json'),
                            AS_DICT,
                            callback)
        for row in rows:
            name = row["META_DATA_ATTR_NAME"]
            value = row["META_DATA_ATTR_VALUE"]
            if name == "name":
                researcherName = value
            elif name == "email":
                researcherEmail = value

        # Send email to researcher notifying him of of the submission of his
        # request
        sendMail(researcherEmail, "[researcher] YOUth data request %s: Data ready" % requestId, "Dear %s,\n\nThe data you have requested is ready for you to download! [instructions here].\n\nWith kind regards,\nYOUth" % researcherName)

        # Set status to OK
        status = 0
        statusInfo = "OK"
    except:
        pass

    return {'status': status, 'statusInfo': statusInfo}


def uuSubmitDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatarequest(callback,
                                                                rule_args[0],
                                                                rei)))


def uuGetDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getDatarequest(callback,
                                                             rule_args[0])))


def uuIsRequestOwner(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isRequestOwner(callback,
                                              rule_args[0], rule_args[1])))


def uuIsReviewer(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isReviewer(callback, rule_args[0],
                                                         rule_args[1])))


def uuAssignRequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(assignRequest(callback,
                                                            rule_args[0],
                                                            rule_args[1])))


def uuSubmitReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitReview(callback,
                                                           rule_args[0],
                                                           rule_args[1], rei)))


def uuGetReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getReview(callback,
                                                        rule_args[0])))


def uuSubmitEvaluation(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitEvaluation(callback,
                                                               rule_args[0],
                                                               rule_args[1],
                                                               rei)))


def uuDTAGrantReadPermissions(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(DTAGrantReadPermissions(callback,
                                              rule_args[0], rule_args[1],
                                              rei)))


def uuRequestDTAReady(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(requestDTAReady(callback,
                                              rule_args[0], rule_args[1])))


def uuSignedDTAGrantReadPermissions(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(signedDTAGrantReadPermissions(
                                              callback, rule_args[0],
                                              rule_args[1], rei)))


def uuRequestDTASigned(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(requestDTASigned(callback,
                                              rule_args[0], rule_args[1])))


def uuRequestDataReady(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(requestDataReady(callback,
                                              rule_args[0], rule_args[1])))
