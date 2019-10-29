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
    zonePath = '/tempZone/home/datarequests-research/'
    timestamp = datetime.now()
    requestId = str(timestamp.strftime('%s'))
    collPath = zonePath + requestId

    # Create collection
    try:
        coll_create(callback, collPath, '1', irods_types.BytesBuf())
    except UUException as e:
        callback.writeString("serverLog", "Could not create collection path.")
        return {"status": "FailedCreateCollectionPath", "statusInfo": "Could not create collection path."}

    # Write data request data to disk
    try:
        filePath = collPath + '/' + 'datarequest.json'
        write_data_object(callback, filePath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write data request to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write data request to disk."}

    # Set the proposal fields as AVUs on the proposal JSON file
    rule_args = [filePath, "-d", "root", data]
    setJsonToObj(rule_args, callback, rei)

    # Set permissions for certain groups on the subcollection
    try:
        set_acl(callback, "recursive", "write", "datarequests-research-datamanagers", collPath)
        set_acl(callback, "recursive", "write", "datarequests-research-data-management-committee", collPath)
        set_acl(callback, "recursive", "write", "datarequests-research-board-of-directors", collPath)
    except UUException as e:
        callback.writeString("serverLog", "Could not set permissions on subcollection.")
        return {"status": "PermissionsError", "statusInfo": "Could not set permissions on subcollection."}

    # Set the status metadata field to "submitted"
    setStatus(callback, requestId, "submitted")

    # Get parameters needed for sending emails
    researcherName = ""
    researcherEmail = ""
    researcherInstitute = ""
    researcherDepartment = ""
    proposalTitle = ""
    submissionDate = timestamp.strftime('%c')
    bodMemberEmails = ""
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
    bodMemberEmails = json.loads(callback.uuGroupGetMembersAsJson("datarequests-research-board-of-directors",
                                                                  bodMemberEmails)['arguments'][1])

    # Send email to researcher and data manager notifying them of the
    # submission of this data request
    sendMail(researcherEmail, "[researcher] YOUth data request %s: submitted" % requestId, "Dear %s,\n\nYour data request has been submitted.\n\nYou will be notified by email of the status of your request. You may also log into Yoda to view the status and other information about your data request.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
    for bodMemberEmail in bodMemberEmails:
        if not bodMemberEmail == "rods":
            sendMail(bodMemberEmail, "[bodmember] YOUth data request %s: submitted" % requestId, "Dear executive board delegate,\n\nA new data request has been submitted.\n\nSubmitted by: %s (%s)\nAffiliation: %s, %s\nDate: %s\nRequest ID: %s\nProposal title: %s\n\nThe following link will take you to the preliminary review form: https://portal.yoda.test/datarequest/preliminaryreview/%s.\n\nWith kind regards,\nYOUth" % (researcherName, researcherEmail, researcherInstitute, researcherDepartment, submissionDate, requestId, proposalTitle, requestId))

    return {'status': 0, 'statusInfo': "OK"}


def getDatarequest(callback, requestId):
    """Retrieve a data request.

       Arguments:
       requestId -- Unique identifier of the data request.
    """

    # Construct filename and filepath
    collName = '/tempZone/home/datarequests-research/' + requestId
    fileName = 'datarequest.json'
    filePath = collName + '/' + fileName

    try:
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
    except Exception as e:
        callback.writeString("serverLog", "Could not get data request status and filesize. (Does a request with this requestID exist?")
        return {"status": "FailedGetDatarequestInfo", "statusInfo": "Could not get data request status and filesize. (Does a request with this requestID exist?)"}

    # Get the contents of the datarequest JSON file
    try:
        requestJSON = read_data_object(callback, filePath)
    except UUException as e:
        callback.writeString("serverLog", "Could not get contents of datarequest JSON file.")
        return {"status": "FailedGetDatarequestContent", "statusInfo": "Could not get contents of datarequest JSON file."}

    return {'requestJSON': requestJSON,
            'requestStatus': requestStatus, 'status': 0,
            'statusInfo': "OK"}


def submitPreliminaryReview(callback, data, requestId, rei):
    """Persist a preliminary review to disk.

       Arguments:
       data       -- JSON-formatted contents of the preliminary review
       proposalId -- Unique identifier of the research proposal
    """
    # Check if user is a member of the Board of Directors. If not, do not
    # allow submission of the preliminary review
    isBoardMember = False
    name = ""

    try:
        isBoardMember = groupUserMember("datarequests-research-board-of-directors",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isBoardMember:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a member of the Board of Directors.")
        return {"status": "PermissionsError", "statusInfo": "User is not a member of the Board of Directors"}

    # Construct path to collection of the evaluation
    zonePath = '/tempZone/home/datarequests-research/'
    collPath = zonePath + requestId

    # Get username
    name = ""
    clientName = callback.uuClientNameWrapper(name)['arguments'][0]

    # Write preliminary review data to disk
    try:
        preliminaryReviewPath = collPath + '/preliminary_review_' + clientName + '.json'
        write_data_object(callback, preliminaryReviewPath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write preliminary review data to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write preliminary review data to disk."}

    # Give read permission on the preliminary review to data managers and Board of Directors members
    try:
        set_acl(callback, "default", "read", "datarequests-research-board-of-directors", preliminaryReviewPath)
        set_acl(callback, "default", "read", "datarequests-research-datamanagers", preliminaryReviewPath)
        set_acl(callback, "default", "read", "datarequests-research-data-management-committee", preliminaryReviewPath)
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the preliminary review file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the preliminary review file."}

    # Get the outcome of the preliminary review (accepted/rejected)
    preliminaryReview = json.loads(data)['preliminary_review']

    # Update the status of the data request
    if preliminaryReview == "Accepted for data manager review":
        setStatus(callback, requestId, "accepted_for_dm_review")
    elif preliminaryReview == "Rejected":
        setStatus(callback, requestId, "preliminary_reject")
    else:
        callback.writeString("serverLog", "Invalid value for preliminary_review in preliminary review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for preliminary_review in preliminary review JSON data."}

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
    if preliminaryReview == "Accepted for data manager review":
        for datamanagerEmail in datamanagerEmails:
            if not datamanagerEmail == "rods":
                sendMail(datamanagerEmail, "[data manager] YOUth data request %s: accepted for data manager review" % requestId, "Dear data manager,\n\nData request %s has been approved for review by the Board of Directors.\n\nYou are now asked to review the data request for any potential problems concerning the requested data.\n\nThe following link will take you directly to the review form: https://portal.yoda.test/datarequest/datamanagerreview/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))
    elif preliminaryReview == "Rejected":
        sendMail(researcherEmail, "[researcher] YOUth data request %s: rejected" % requestId, "Dear %s,\n\nYour data request has been rejected for the following reason(s):\n\n%s\n\nIf you wish to object against this rejection, please contact the YOUth data manager (%s).\n\nWith kind regards,\nYOUth" % (researcherName, json.loads(data)['feedback_for_researcher'], datamanagerEmails[0]))
    else:
        callback.writeString("serverLog", "Invalid value for preliminary_review in preliminary review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for preliminary_review in preliminary review JSON data."}

    return {'status': 0, 'statusInfo': "OK"}


def getPreliminaryReview(callback, requestId):
    """Retrieve a preliminary review.

       Arguments:
       requestId -- Unique identifier of the preliminary review
    """
    # Construct filename
    collName = '/tempZone/home/datarequests-research/' + requestId
    fileName = 'preliminary_review_bodmember.json'

    # Get the size of the preliminary review JSON file and the review's status
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
    try:
        preliminaryReviewJSON = read_data_object(callback, filePath)
    except UUException as e:
        callback.writeString("serverLog", "Could not get preliminary review data.")
        return {"status": "ReadError", "statusInfo": "Could not get preliminary review data."}

    return {'preliminaryReviewJSON': preliminaryReviewJSON, 'status': 0, 'statusInfo': "OK"}


def submitDatamanagerReview(callback, data, requestId, rei):
    """Persist a preliminary review to disk.

       Arguments:
       data       -- JSON-formatted contents of the preliminary review
       proposalId -- Unique identifier of the research proposal
    """
    # Check if user is a data manager. If not, do not the user to assign the
    # request
    isDatamanager = False
    name = ""

    try:
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isDatamanager:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a data manager.")
        return {"status": "PermissionDenied", "statusInfo": "User is not a data manager."}

    # Construct path to collection of the evaluation
    zonePath = '/tempZone/home/datarequests-research/'
    collPath = zonePath + requestId

    # Get username
    name = ""
    clientName = callback.uuClientNameWrapper(name)['arguments'][0]

    # Write data manager review data to disk
    try:
        datamanagerReviewPath = collPath + '/datamanager_review_' + clientName + '.json'
        write_data_object(callback, datamanagerReviewPath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write data manager review data to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write data manager review data to disk."}

    # Give read permission on the data manager review to data managers and Board of Directors members
    try:
        set_acl(callback, "default", "read", "datarequests-research-board-of-directors", datamanagerReviewPath)
        set_acl(callback, "default", "read", "datarequests-research-datamanagers", datamanagerReviewPath)
        set_acl(callback, "default", "read", "datarequests-research-data-management-committee", datamanagerReviewPath)
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the preliminary review file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the preliminary review file."}

    # Get the outcome of the data manager review (accepted/rejected)
    datamanagerReview = json.loads(data)['datamanager_review']

    # Update the status of the data request
    if datamanagerReview == "Accepted":
        setStatus(callback, requestId, "dm_accepted")
    elif datamanagerReview == "Rejected":
        setStatus(callback, requestId, "dm_rejected")
    else:
        callback.writeString("serverLog", "Invalid value for datamanager_review in data manager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for datamanager_review in data manager review JSON data."}

    # Get parameters needed for sending emails
    researcherName = ""
    researcherEmail = ""
    bodMemberEmails = ""
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
    bodMemberEmails = json.loads(callback.uuGroupGetMembersAsJson("datarequests-research-board-of-directors",
                                                                  bodMemberEmails)['arguments'][1])

    # Send emails to:
    # - the researcher: progress update
    # - the board of directors: call to action
    if datamanagerReview == "Accepted":
        for bodMemberEmail in bodMemberEmails:
            if not bodMemberEmail == "rods":
                sendMail(bodMemberEmail, "[bod member] YOUth data request %s: accepted by data manager" % requestId, "Dear executive board delegate,\n\nData request %s has been accepted by the data manager.\n\nYou are now asked to assign the data request for review to one or more DMC members. To do so, please navigate to the assignment form using this link: https://portal.yoda.test/datarequest/assign/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))
    elif datamanagerReview == "Rejected":
        for bodMemberEmail in bodMemberEmails:
            if not bodMemberEmail == "rods":
                sendMail(bodMemberEmail, "[bod member] YOUth data request %s: rejected by data manager" % requestId, "Dear executive board delegate,\n\nData request %s has been rejected by the data manager for the following reason(s):\n\n%s\n\nThe data manager's review is advisory. Please consider the objections raised and then either reject the data request or assign it for review to one or more DMC members. To do so, please navigate to the assignment form using this link https://portal.yoda.test/datarequest/assign/%s.\n\nWith kind regards,\nYOUth" % (requestId, json.loads(data)['datamanager_remarks'], requestId))
    else:
        callback.writeString("serverLog", "Invalid value for datamanager_review in data manager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for datamanager_review in data manager review JSON data."}

    return {'status': 0, 'statusInfo': "OK"}


def getDatamanagerReview(callback, requestId):
    """Retrieve a data manager review.

       Arguments:
       requestId -- Unique identifier of the data manager review
    """
    # Construct filename
    collName = '/tempZone/home/datarequests-research/' + requestId
    fileName = 'datamanager_review_datamanager.json'

    # Get the size of the data manager review JSON file and the review's status
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

    # Get the contents of the data manager review JSON file
    try:
        datamanagerReviewJSON = read_data_object(callback, filePath)
    except UUException as e:
        callback.writeString("serverLog", "Could not get data manager review data.")
        return {"status": "ReadError", "statusInfo": "Could not get data manager review data."}

    return {'datamanagerReviewJSON': datamanagerReviewJSON, 'status': 0, 'statusInfo': "OK"}


def isRequestOwner(callback, requestId, currentUserName):
    """Check if the invoking user is also the owner of a given data request.

       Arguments:
       requestId       -- Unique identifier of the data request.
       currentUserName -- Username of the user whose ownership is checked.

       Return:
       dict -- A JSON dict specifying whether the user owns the data request.
    """
    isRequestOwner = True

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
        callback.writeString("serverLog", "Not exactly 1 owner of data request found. Something is very wrong.")
        return {"status": "MoreThanOwnOwner", "statusInfo": "Not exactly 1 owner of data request found. Something is very wrong."}

    # We only have 1 owner. Set requestOwnerUserName to this owner
    requestOwnerUserName = requestOwnerUserName[0]

    # Compare the request owner username to the username of the current
    # user to determine ownership
    isRequestOwner = requestOwnerUserName == currentUserName

    # Return data
    return {'isRequestOwner': isRequestOwner, 'status': 0, 'statusInfo': "OK"}


def isReviewer(callback, requestId, currentUsername):
    """Check if the invoking user is assigned as reviewer to the given data request.

       Arguments:
       requestId       -- Unique identifier of the data request.
       currentUserName -- Username of the user that is to be checked.

       Return:
       dict -- A JSON dict specifying whether the user is assigned as reviewer to the data request.
    """
    isReviewer = False

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

    # Return the isReviewer boolean
    return {"isReviewer": isReviewer, "status": 0, "statusInfo": "OK"}


def submitAssignment(callback, data, requestId, rei):
    """Persist an assignment to disk.

       Arguments:
       data       -- JSON-formatted contents of the assignment
       proposalId -- Unique identifier of the research proposal
    """
    # Check if user is a member of the Board of Directors. If not, do not
    # allow assignment
    isBoardMember = False
    name = ""

    try:
        isBoardMember = groupUserMember("datarequests-research-board-of-directors",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isBoardMember:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a member of the Board of Directors.")
        return {"status": "PermissionsError", "statusInfo": "User is not a member of the Board of Directors"}

    # Construct path to collection of the evaluation
    zonePath = '/tempZone/home/datarequests-research/'
    collPath = zonePath + requestId

    # Get username
    name = ""
    clientName = callback.uuClientNameWrapper(name)['arguments'][0]

    # Write assignment data to disk
    try:
        assignmentPath = collPath + '/assignment_' + clientName + '.json'
        write_data_object(callback, assignmentPath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write assignment data to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write assignment data to disk."}

    # Give read permission on the assignment to data managers and Board of Directors members
    try:
        set_acl(callback, "default", "read", "datarequests-research-board-of-directors", assignmentPath)
        set_acl(callback, "default", "read", "datarequests-research-datamanagers", assignmentPath)
        set_acl(callback, "default", "read", "datarequests-research-data-management-committee", assignmentPath)
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the assignment file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the assignment file."}

    # Get the outcome of the assignment (accepted/rejected)
    decision = json.loads(data)['decision']

    # If the data request has been accepted for DMC review, get the assignees
    # assignees = json.loads(data)['assign_to']
    # Use dummy assignee value for now
    assignees = json.dumps(['dmcmember'])

    # Update the status of the data request
    if decision == "Accepted for DMC review":
        assignRequest(callback, assignees, requestId)
        setStatus(callback, requestId, "assigned")
    elif decision == "Rejected":
        setStatus(callback, requestId, "rejected_after_data_manager_review")
    else:
        callback.writeString("serverLog", "Invalid value for 'decision' key in datamanager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'decision' key in datamanager review JSON data."}

    # Get email parameters
    requestColl = ('/tempZone/home/datarequests-research/' + requestId)
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

    # Send emails to the researcher (and to the assignees if the data request has been accepted for DMC review)
    if decision == "Accepted for DMC review":
        sendMail(researcherEmail, "[researcher] YOUth data request %s: assigned" % requestId, "Dear %s,\n\nYour data request has been assigned for review by the YOUth data manager.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
        callback.writeString("serverLog", assignees)
        for assigneeEmail in json.loads(assignees):
            sendMail(assigneeEmail, "[assignee] YOUth data request %s: assigned" % requestId, "Dear DMC member,\n\nData request %s (proposal title: \"%s\") has been assigned to you for review. Please sign in to Yoda to view the data request and submit your review.\n\nThe following link will take you directly to the review form: https://portal.yoda.test/datarequest/review/%s.\n\nWith kind regards,\nYOUth" % (requestId, proposalTitle, requestId))
    elif decision == "Rejected":
        sendMail(researcherEmail, "[researcher] YOUth data request %s: rejected" % requestId, "Dear %s,\n\nYour data request has been rejected for the following reason(s):\n\n%s\n\nIf you wish to object against this rejection, please contact the YOUth data manager.\n\nWith kind regards,\nYOUth" % (researcherName, json.loads(data)['feedback_for_researcher']))
    else:
        callback.writeString("serverLog", "Invalid value for 'decision' key in datamanager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'decision' key in datamanager review JSON data."}

    return {'status': 0, 'statusInfo': "OK"}


def assignRequest(callback, assignees, requestId):
    """Assign a data request to one or more DMC members for review.

       Arguments:
       assignees -- JSON-formatted array of DMC members.
       requestId -- Unique identifier of the data request

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    # Check if user is a data manager. If not, do not the user to assign the
    # request
    isDatamanager = False
    name = ""

    try:
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isDatamanager:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a data manager.")
        return {"status": "PermissionDenied", "statusInfo": "User is not a data manager."}

    # Construct data request collection path
    requestColl = ('/tempZone/home/datarequests-research/' + requestId)

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

    if not (requestStatus == "dm_accepted" or requestStatus == "dm_rejected"):
        callback.writeString("serverLog", "Proposal is already assigned.")
        return {"status": "AlreadyAssigned", "statusInfo": "Proposal is already assigned."}

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

    return {'status': 0, 'statusInfo': "OK"}


def getAssignment(callback, requestId):
    """Retrieve assignment.

       Arguments:
       requestId -- Unique identifier of the assignment
    """
    # Construct filename
    collName = '/tempZone/home/datarequests-research/' + requestId
    fileName = 'assignment_bodmember.json'

    # Get the size of the assignment JSON file and the review's status
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

    # Get the contents of the assignment JSON file
    try:
        assignmentJSON = read_data_object(callback, filePath)
    except UUException as e:
        callback.writeString("serverLog", "Could not get assignment data.")
        return {"status": "ReadError", "statusInfo": "Could not get assignment data."}

    return {'assignmentJSON': assignmentJSON, 'status': 0, 'statusInfo': "OK"}


def submitReview(callback, data, requestId, rei):
    """Persist a data request review to disk.

       Arguments:
       data -- JSON-formatted contents of the data request review
       proposalId -- Unique identifier of the research proposal

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    # Check if user is a member of the Data Management Committee. If not, do
    # not allow submission of the review
    isDmcMember = False
    name = ""

    try:
        isDmcMember = groupUserMember("datarequests-research-data-management-committee",
                                      callback.uuClientFullNameWrapper(name)
                                      ['arguments'][0], callback)

        if not isDmcMember:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a member of the Data Management Committee.")
        return {"status": "PermissionDenied", "statusInfo": "User is not a member of the Data Management Committee."}

    # Check if the user has been assigned as a reviewer. If not, do not
    # allow submission of the review
    name = ""
    username = callback.uuClientNameWrapper(name)['arguments'][0]

    try:
        if not isReviewer(callback, requestId, username)['isReviewer']:
            raise UUException
    except UUException as e:
        callback.writeString("serverLog", "User is not assigned as a reviewer to this request.")
        return {"status": "PermissionDenied", "statusInfo": "User is not assigned as a reviewer to this request."}

    # Construct path to collection of review
    zonePath = '/tempZone/home/datarequests-research/'
    collPath = zonePath + requestId

    # Get username
    name = ""
    clientName = callback.uuClientNameWrapper(name)['arguments'][0]

    # Write review data to disk
    try:
        reviewPath = collPath + '/review_' + clientName + '.json'
        write_data_object(callback, reviewPath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write review data to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write review data to disk."}

    # Give read permission on the review to Board of Director members
    try:
        set_acl(callback, "default", "read", "datarequests-research-board-of-directors", reviewPath)
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the review file to the Board of Directors.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the review file to the Board of Directors"}

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
                sendMail(bodmemberEmail, "[bod member] YOUth data request %s: reviewed" % requestId, "Dear Board of Directors member,\n\nData request %s has been reviewed by the YOUth data management committee and is awaiting your final evaluation.\n\nPlease log into Yoda to evaluate the data request.\n\nThe following link will take you directly to the evaluation form: https://portal.yoda.test/datarequest/evaluate/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))

    return {'status': 0, 'statusInfo': "OK"}


def getReview(callback, requestId):
    """Retrieve a data request review.

       Arguments:
       requestId -- Unique identifier of the data request
    """
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
    try:
        reviewJSON = read_data_object(callback, filePath)
    except UUException as e:
        callback.writeString("serverLog", "Could not get review data.")
        return {"status": "ReadError", "statusInfo": "Could not get review data."}

    return {'reviewJSON': reviewJSON, 'status': 0, 'statusInfo': "OK"}


def submitEvaluation(callback, data, requestId, rei):
    """Persist an evaluation to disk.

       Arguments:
       data       -- JSON-formatted contents of the evaluation
       proposalId -- Unique identifier of the research proposal
    """
    # Check if user is a member of the Board of Directors. If not, do not
    # allow submission of the evaluation
    isBoardMember = False
    name = ""

    try:
        isBoardMember = groupUserMember("datarequests-research-board-of-directors",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isBoardMember:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a member of the Board of Directors.")
        return {"status": "PermissionsError", "statusInfo": "User is not a member of the Board of Directors"}

    # Construct path to collection of the evaluation
    zonePath = '/tempZone/home/datarequests-research/'
    collPath = zonePath + requestId

    # Get username
    name = ""
    clientName = callback.uuClientNameWrapper(name)['arguments'][0]

    # Write evaluation data to disk
    try:
        evaluationPath = collPath + '/evaluation_' + clientName + '.json'
        write_data_object(callback, evaluationPath, data)
    except UUException as e:
        callback.writeString("serverLog", "Could not write evaluation data to disk.")
        return {"status": "WriteError", "statusInfo": "Could not write evaluation data to disk."}

    # Get outcome of evaluation
    decision = json.loads(data)['evaluation']

    # Update the status of the data request
    if decision == "Approved":
        setStatus(callback, requestId, "approved")
    elif decision == "Rejected":
        setStatus(callback, requestId, "rejected")
    else:
        callback.writeString("serverLog", "Invalid value for 'evaluation' key in evaluation JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'evaluation' key in evaluation JSON data."}
        
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
    if decision == "Approved":
        sendMail(researcherEmail, "[researcher] YOUth data request %s: approved" % requestId, "Dear %s,\n\nCongratulations! Your data request has been approved. The YOUth data manager will now create a Data Transfer Agreement for you to sign. You will be notified when it is ready.\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, requestId))
        for datamanagerEmail in datamanagerEmails:
            if not datamanagerEmail == "rods":
                sendMail(datamanagerEmail, "[data manager] YOUth data request %s: approved" % requestId, "Dear data manager,\n\nData request %s has been approved by the Board of Directors. Please sign in to Yoda to upload a Data Transfer Agreement for the researcher.\n\nThe following link will take you directly to the data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (requestId, requestId))
    elif decision == "Rejected":
        sendMail(researcherEmail, "[researcher] YOUth data request %s: rejected" % requestId, "Dear %s,\n\nYour data request has been rejected for the following reason(s):\n\n%s\n\nIf you wish to object against this rejection, please contact the YOUth data manager (%s).\n\nThe following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/%s.\n\nWith kind regards,\nYOUth" % (researcherName, json.loads(data)['feedback_for_researcher'], datamanagerEmails[0], requestId))
    else:
        callback.writeString("serverLog", "Invalid value for 'evaluation' key in evaluation JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'evaluation' key in evaluation JSON data."}

    return {'status': 0, 'statusInfo': "OK"}


def DTAGrantReadPermissions(callback, requestId, username, rei):
    """Grant read permissions on the DTA to the owner of the associated data request.

       Arguments:
       requestId --
       username  --
    """
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
        callback.writeString("serverLog", "Not exactly 1 owner found. Something is very wrong.")
        return {"status": "MoreThanOneOwner", "statusInfo": "Not exactly 1 owner found. Something is very wrong."}

    requestOwnerUsername = requestOwnerUsername[0]

    try:
        set_acl(callback, "default", "read", requestOwnerUsername, collPath + "/dta.pdf")
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the DTA to the data request owner.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the DTA to the data request owner."}

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

    return {'status': 0, 'statusInfo': "OK"}


def requestDTAReady(callback, requestId, currentUserName):
    """Set the status of a submitted datarequest to "DTA ready".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose ownership is checked.
    """
    # Check if the user requesting the status transition is a data manager.
    # If not, do not allow status transition
    isDatamanager = False
    name = ""

    try:
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isDatamanager:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a data manager.")
        return {"status": "PermissionsError", "statusInfo": "User is not a data manager."}

    setStatus(callback, requestId, "dta_ready")

    return {'status': 0, 'statusInfo': "OK"}


def signedDTAGrantReadPermissions(callback, requestId, username, rei):
    """Grant read permissions on the signed DTA to the datamanagers group.

       Arguments:
       requestId -- Unique identifier of the datarequest.
       username  --
    """
    # Construct path to the collection of the datarequest
    zoneName = ""
    clientZone = callback.uuClientZone(zoneName)['arguments'][0]
    collPath = ("/" + clientZone + "/home/datarequests-research/" +
                requestId)

    try:
        set_acl(callback, "default", "read", "datarequests-research-datamanagers", collPath + "/signed_dta.pdf")
    except UUException as e:
        callback.writeString("serverLog", "Could not grant read permissions on the signed DTA to the data managers group.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the signed DTA to the data managers group."}

    # Get parameters needed for sending emails
    datamanagerEmails = ""
    datamanagerEmails = json.loads(callback.uuGroupGetMembersAsJson('datarequests-research-datamanagers', datamanagerEmails)['arguments'][1])

    # Send an email to the data manager informing them that the DTA has been
    # signed by the researcher
    for datamanagerEmail in datamanagerEmails:
        if not datamanagerEmail == "rods":
            sendMail(datamanagerEmail, "[data manager] YOUth data request %s: DTA signed" % requestId, "Dear data manager,\n\nThe researcher has uploaded a signed copy of the Data Transfer Agreement for data request %s.\n\nPlease log in to Yoda to review this copy. The following link will take you directly to the data request: https://portal.yoda.test/datarequest/view/%s.\n\nAfter verifying that the document has been signed correctly, you may prepare the data for download. When the data is ready for the researcher to download, please click the \"Data ready\" button. This will notify the researcher by email that the requested data is ready. The email will include instructions on downloading the data.\n\nWith kind regards,\nYOUth" % (requestId, requestId))

    return {'status': 0, 'statusInfo': "OK"}


def requestDTASigned(callback, requestId, currentUserName):
    """Set the status of a data request to "DTA signed".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose role is checked.
    """
    # Check if uploading user owns the datarequest and only allow uploading
    # if this is the case
    try:
        result = isRequestOwner(callback, requestId, currentUserName)
        if not result['isRequestOwner']:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User does not own the request.")
        return {"status": "PermissionsError", "statusInfo": "User does not own the request."}

    setStatus(callback, requestId, "dta_signed")

    return {'status': 0, 'statusInfo': "OK"}


def requestDataReady(callback, requestId, currentUserName):
    """Set the status of a submitted datarequest to "Data ready".

       Arguments:
       requestId       -- Unique identifier of the datarequest.
       currentUserName -- Username of the user whose ownership is checked.
    """
    # Check if the user requesting the status transition is a data manager.
    # If not, do not allow status transition
    isDatamanager = False
    name = ""

    try:
        isDatamanager = groupUserMember("datarequests-research-datamanagers",
                                        callback.uuClientFullNameWrapper(name)
                                        ['arguments'][0],
                                        callback)

        if not isDatamanager:
            raise Exception
    except Exception as e:
        callback.writeString("serverLog", "User is not a data manager.")
        return {"status": "PermissionsError", "statusInfo": "User is not a data manager."}

    setStatus(callback, requestId, "data_ready")

    # Get parameters needed for sending emails
    researcherName = ""
    researcherEmail = ""
    rows = row_iterator(["META_DATA_ATTR_NAME", "META_DATA_ATTR_VALUE"],
                        ("COLL_NAME = '%s' AND " +
                         "DATA_NAME = '%s'") % (requestId,
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

    return {'status': 0, 'statusInfo': "OK"}


def uuSubmitDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatarequest(callback,
                                                                rule_args[0],
                                                                rei)))


def uuGetDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getDatarequest(callback,
                                                             rule_args[0])))


def uuSubmitPreliminaryReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitPreliminaryReview(callback, rule_args[0], rule_args[1], rei)))


def uuGetPreliminaryReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getPreliminaryReview(callback, rule_args[0])))


def uuSubmitDatamanagerReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatamanagerReview(callback, rule_args[0], rule_args[1], rei)))


def uuGetDatamanagerReview(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getDatamanagerReview(callback, rule_args[0])))


def uuIsRequestOwner(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isRequestOwner(callback,
                                              rule_args[0], rule_args[1])))


def uuIsReviewer(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(isReviewer(callback, rule_args[0],
                                                         rule_args[1])))


def uuSubmitAssignment(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitAssignment(callback, rule_args[0], rule_args[1], rei)))


def uuAssignRequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(assignRequest(callback,
                                                            rule_args[0],
                                                            rule_args[1])))


def uuGetAssignment(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getAssignment(callback, rule_args[0])))


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
