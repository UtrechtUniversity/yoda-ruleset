# -*- coding: utf-8 -*-
"""Functions to handle data requests."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'
__author__    = ('Lazlo Westerhof, Jelmer Zondergeld')

from datetime import datetime
from genquery import (row_iterator, AS_DICT)
import json

from util import *
import mail

__all__ = ['api_datarequest_submit',
           'api_datarequest_get',
           'api_datarequest_is_owner',
           'api_datarequest_is_reviewer',
           'api_datarequest_preliminary_review_submit',
           'api_datarequest_preliminary_review_get',
           'api_datarequest_datamanager_review_submit',
           'api_datarequest_datamanager_review_get',
           'api_datarequest_assignment_submit',
           'api_datarequest_assignment_get',
           'api_datarequest_review_submit',
           'api_datarequest_reviews_get',
           'api_datarequest_evaluation_submit',
           'api_datarequest_dta_post_upload_actions',
           'api_datarequest_signed_dta_post_upload_actions',
           'api_datarequest_data_ready']


def get_group_data(ctx):
    """Return groups and related data.

       Copied from irods-ruleset-uu/uuGroup.py.
    """
    groups = {}

    # First query: obtain a list of groups with group attributes.
    iter = row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup'",
        genquery.AS_LIST, ctx)

    for row in iter:
        name = row[0]
        attr = row[1]
        value = row[2]

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

    # Second query: obtain list of groups with memberships.
    iter = row_iterator(
        "USER_GROUP_NAME, USER_NAME, USER_ZONE",
        "USER_TYPE != 'rodsgroup'",
        genquery.AS_LIST, ctx)

    for row in iter:
        name = row[0]
        user = row[1]
        zone = row[2]

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

    return groups.values()


def set_status(ctx, request_id, status):
    """Set the status of a data request

       Arguments:
       request_id -- Unique identifier of the data request.
       status    -- The status to which the data request should be set.
    """
    set_metadata(ctx, request_id, "status", status)


def get_status(ctx, request_id):
    """Get the status of a data request

       Arguments:
       request_id -- Unique identifier of the data request.
    """
    # Construct filename and filepath
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'datarequest.json'
    file_path = coll_name + '/' + file_name

    try:
        rows = row_iterator(["META_DATA_ATTR_VALUE"],
                            ("COLL_NAME = '%s' AND DATA_NAME = '%s' AND "
                             + "META_DATA_ATTR_NAME = 'status'") % (coll_name,
                                                                    file_name),
                            AS_DICT, ctx)

        for row in rows:
            request_status = row['META_DATA_ATTR_VALUE']
    except Exception:
        log.write(ctx, "Could not get data request status.")
        return {"status": "FailedGetDatarequestStatus", "statusInfo": "Could not get data request status."}

    return request_status


def set_metadata(ctx, request_id, key, value):
    """Set an arbitrary metadata field on a data request

       Arguments:
       request_id -- Unique identifier of the data request.
       key        -- Key of the metdata field
       value      -- Value of the meta field
    """

    # Construct path to the collection of the data request
    client_zone = user.zone(ctx)
    request_coll = ("/" + client_zone + "/home/datarequests-research/"
                    + request_id)

    # Add delayed rule to update data request status
    response_status = ""
    response_status_info = ""
    ctx.requestDatarequestMetadataChange(request_coll, key,
                                         value, 0, response_status,
                                         response_status_info)

    # Trigger the processing of delayed rules
    ctx.adminDatarequestActions()


@api.make()
def api_datarequest_submit(ctx, data, previous_request_id):
    """Persist a data request to disk.

       Arguments:
       data -- Contents of the data request.
    """
    zone_path = '/tempZone/home/datarequests-research/'
    timestamp = datetime.now()
    request_id = str(timestamp.strftime('%s'))
    coll_path = zone_path + request_id

    # Create collection
    try:
        collection.create(ctx, coll_path)
    except Exception:
        log.write(ctx, "Could not create collection path.")
        return api.Error("create_collection_fail", "Could not create collection path.")

    # Write data request data to disk
    try:
        datarequest_path = coll_path + '/' + 'datarequest.json'
        jsonutil.write(ctx, datarequest_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write datarequest to disk')

    # Set the previous request ID as metadata if defined
    if previous_request_id:
        set_metadata(ctx, request_id, "previous_request_id", previous_request_id)

    # Set permissions for certain groups on the subcollection
    try:
        msi.set_acl(ctx, "recursive", "write", "datarequests-research-datamanagers", coll_path)
        msi.set_acl(ctx, "recursive", "write", "datarequests-research-data-management-committee", coll_path)
        msi.set_acl(ctx, "recursive", "write", "datarequests-research-board-of-directors", coll_path)
    except Exception:
        log.write(ctx, "Could not set permissions on subcollection.")
        return api.Error("permission_error", "Could not set permissions on subcollection.")

    # Set the status metadata field to "submitted"
    set_status(ctx, request_id, "submitted")

    # Get parameters needed for sending emails
    datarequest = json.loads(data)

    contact = datarequest['researchers']['contacts'][0]
    research_context = datarequest['research_context']

    researcher_name        = contact['name']
    researcher_email       = contact['email']
    researcher_institution = contact['institution']
    researcher_department  = contact['department']
    proposal_title         = research_context['title']
    submission_date        = timestamp.strftime('%c')
    bod_member_emails = json.loads(ctx.uuGroupGetMembersAsJson(
                                   "datarequests-research-board-of-directors", "")['arguments'][1])

    # Send email to researcher and board of directors member(s)
    mail_datarequest_researcher(ctx, researcher_email, researcher_name, request_id)
    for bodmember_email in bod_member_emails:
        if not bodmember_email == "rods":
            mail_datarequest_bodmember(ctx, bodmember_email, request_id, researcher_name,
                                       researcher_email, researcher_institution,
                                       researcher_department, submission_date, proposal_title)


@api.make()
def api_datarequest_get(ctx, request_id):
    """Retrieve a data request.

       Arguments:
       request_id -- Unique identifier of the data request.
    """
    # Convert request_id to string if it isn't already
    request_id = str(request_id)

    # Check if user is allowed to view to proposal. If not, return
    # PermissionError
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")
        isdmcmember   = user.is_member_of(ctx, "datarequests-research-data-management-committee")
        isrequestowner = datarequest_is_owner(ctx, request_id, user.name(ctx))['owner']

        if not (isboardmember or isdatamanager or isdmcmember or isrequestowner):
            log.write(ctx, "User is not authorized to view this data request.")
            return api.Error("permission_error", "User is not authorized to view this data request.")
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return api.Error("permission_error", "Something went wrong during permission checking.")

    # Construct filename and filepath
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'datarequest.json'
    file_path = coll_name + '/' + file_name

    try:
        # Get the size of the datarequest JSON file and the request's status
        rows = row_iterator(["DATA_SIZE", "COLL_NAME", "META_DATA_ATTR_VALUE"],
                            "COLL_NAME = '%s'" % coll_name
                            + " AND DATA_NAME = '%s'" % file_name
                            + " AND META_DATA_ATTR_NAME = 'status'",
                            AS_DICT, ctx)
        for row in rows:
            coll_name = row['COLL_NAME']
            request_status = row['META_DATA_ATTR_VALUE']
    except Exception:
        log.write(ctx, "Could not get data request status and filesize. (Does a request with this requestID exist?")
        return api.Error("failed_get_datarequest_info", "Could not get data request status and filesize. (Does a request with this requestID exist?)")

    # Get the contents of the datarequest JSON file
    try:
        request_json = data_object.read(ctx, file_path)
    except Exception:
        log.write(ctx, "Could not get contents of datarequest JSON file.")
        return api.Error("datarequest_read_fail", "Could not get contents of datarequest JSON file.")

    return {'requestJSON': request_json, 'requestStatus': request_status}


@api.make()
def api_datarequest_preliminary_review_submit(ctx, data, request_id):
    """Persist a preliminary review to disk.

       Arguments:
       data       -- Contents of the preliminary review
       request_id -- Unique identifier of the research proposal
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Read data into a dictionary
    preliminary_review = json.loads(data)

    # Check if user is a member of the Board of Directors. If not, do not
    # allow submission of the preliminary review
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")

        if not isboardmember:
            log.write(ctx, "User is not a member of the Board of Directors.")
            return {'status': "PermissionError", 'statusInfo': "User is not a member of the Board of Directors"}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Check if status is appropriate for the submission of the preliminary review
    if not get_status(ctx, request_id) == "submitted":
        log.write(ctx, "Current status of data request does not permit this operation.")
        return {"status": "PermissionError", "statusInfo": "Current status of data request does not permit this operation."}

    # Construct path to collection of the evaluation
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    # Get username
    client_name = user.name(ctx)

    # Write preliminary review data to disk
    try:
        preliminary_review_path = coll_path + '/preliminary_review_' + client_name + '.json'
        jsonutil.write(ctx, preliminary_review_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write preliminary review data to disk')

    # Give read permission on the preliminary review to data managers and Board of Directors members
    try:
        msi.set_acl(ctx, "default", "read", "datarequests-research-board-of-directors", preliminary_review_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-datamanagers", preliminary_review_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-data-management-committee", preliminary_review_path)
    except Exception:
        log.write(ctx, "Could not grant read permissions on the preliminary review file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the preliminary review file."}

    # Get the outcome of the preliminary review (accepted/rejected)
    decision = preliminary_review['preliminary_review']

    # Update the status of the data request
    if decision == "Accepted for data manager review":
        set_status(ctx, request_id, "accepted_for_dm_review")
    elif decision == "Rejected":
        set_status(ctx, request_id, "preliminary_reject")
    elif decision == "Rejected (resubmit)":
        set_status(ctx, request_id, "preliminary_reject_submit")
    else:
        log.write(ctx, "Invalid value for preliminary_review in preliminary review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for preliminary_review in preliminary review JSON data."}

    # Get parameters needed for sending emails
    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    researcher = datarequest['researchers']['contacts'][0]

    researcher_name = researcher['name']
    researcher_email = researcher['email']

    if 'feedback_for_researcher' in preliminary_review:
        feedback_for_researcher = preliminary_review['feedback_for_researcher']

    datamanager_emails = json.loads(ctx.uuGroupGetMembersAsJson('datarequests-research-datamanagers',
                                    "")['arguments'][1])

    # Send an email to the researcher informing them of whether their data request has been approved
    # or rejected
    if decision == "Accepted for data manager review":
        for datamanager_email in datamanager_emails:
            if not datamanager_email == "rods":
                mail_preliminary_review_accepted(ctx, datamanager_email, request_id)
    elif decision == "Rejected (resubmit)":
        mail_preliminary_review_resubmit(ctx, decision, researcher_email, researcher_name,
                                         feedback_for_researcher, datamanager_emails[0], request_id)
    elif decision == "Rejected":
        mail_preliminary_review_rejected(ctx, decision, researcher_email, researcher_name,
                                         feedback_for_researcher, datamanager_emails[0], request_id)


@api.make()
def api_datarequest_preliminary_review_get(ctx, request_id):
    """Retrieve a preliminary review.

       Arguments:
       request_id -- Unique identifier of the preliminary review
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is authorized. If not, return PermissionError
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")
        isreviewer = datarequest_is_reviewer(ctx, request_id)

        if not (isboardmember or isdatamanager or isreviewer):
            log.write(ctx, "User is not authorized to view this preliminary review.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to view this preliminary review."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Construct filename
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'preliminary_review_bodmember.json'

    # Get the size of the preliminary review JSON file and the review's status
    rows = row_iterator(["DATA_SIZE", "DATA_NAME", "COLL_NAME"],
                        "COLL_NAME = '%s' AND " % coll_name
                        + "DATA_NAME like '%s'" % file_name,
                        AS_DICT, ctx)
    for row in rows:
        coll_name = row['COLL_NAME']
        data_name = row['DATA_NAME']
        data_size = row['DATA_SIZE']

    # Construct path to file
    file_path = coll_name + '/' + data_name

    # Get the contents of the review JSON file
    try:
        preliminary_review_json = data_object.read(ctx, file_path)
    except Exception:
        log.write(ctx, "Could not get preliminary review data.")
        return {"status": "ReadError", "statusInfo": "Could not get preliminary review data."}

    return preliminary_review_json


@api.make()
def api_datarequest_datamanager_review_submit(ctx, data, request_id):
    """Persist a datamanager review to disk.

       Arguments:
       data       -- Contents of the preliminary review
       proposalId -- Unique identifier of the research proposal
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Read datamanager review into a dictionary
    datamanager_review = json.loads(data)

    # Check if user is a data manager. If not, do not the user to assign the
    # request
    try:
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")

        if not isdatamanager:
            log.write(ctx, "User is not a data manager.")
            return {"status": "PermissionError", "statusInfo": "User is not a data manager."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Check if status is appropriate for the submission of the data manager review
    if not get_status(ctx, request_id) == 'accepted_for_dm_review':
        log.write(ctx, "Current status of data request does not permit this operation.")
        return {"status": "PermissionError", "statusInfo": "Current status of data request does not permit this operation."}

    # Construct path to collection of the evaluation
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    # Get username
    client_name = user.name(ctx)

    # Write data manager review data to disk
    try:
        datamanager_review_path = coll_path + '/datamanager_review_' + client_name + '.json'
        jsonutil.write(ctx, datamanager_review_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write data manager review data to disk')

    # Give read permission on the data manager review to data managers and Board of Directors members
    try:
        msi.set_acl(ctx, "default", "read", "datarequests-research-board-of-directors", datamanager_review_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-datamanagers", datamanager_review_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-data-management-committee", datamanager_review_path)
    except Exception:
        log.write(ctx, "Could not grant read permissions on the preliminary review file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the preliminary review file."}

    # Get the outcome of the data manager review (accepted/rejected)
    decision = datamanager_review['datamanager_review']

    # Update the status of the data request
    if decision == "Accepted":
        set_status(ctx, request_id, "dm_accepted")
    elif decision == "Rejected":
        set_status(ctx, request_id, "dm_rejected")
    elif decision == "Rejected (resubmit)":
        set_status(ctx, request_id, "dm_rejected_resubmit")
    else:
        log.write(ctx, "Invalid value for decision in data manager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for decision in data manager review JSON data."}

    # Get parameters needed for sending emails
    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    researcher = datarequest['researchers']['contacts'][0]

    researcher_name = researcher['name']
    researcher_email = researcher['email']

    if 'datamanager_remarks' in datamanager_review:
        datamanager_remarks = datamanager_review['datamanager_remarks']
    else:
        datamanager_remarks = None

    bod_member_emails = json.loads(ctx.uuGroupGetMembersAsJson("datarequests-research-board-of-directors",
                                                               "")['arguments'][1])

    # Send emails to:
    # - the board of directors: call to action
    for bod_member_email in bod_member_emails:
        if not bod_member_email == "rods":
            if decision == "Accepted":
                mail_datamanager_review_accepted(ctx, decision, bod_member_email, request_id)
            elif decision == "Rejected (resubmit)":
                mail_datamanager_review_resubmit(ctx, decision, bod_member_email,
                                                 datamanager_remarks, request_id)
            elif decision == "Rejected":
                mail_datamanager_review_rejected(ctx, decision, bod_member_email,
                                                 datamanager_remarks, request_id)



@api.make()
def api_datarequest_datamanager_review_get(ctx, request_id):
    """Retrieve a data manager review.

       Arguments:
       request_id -- Unique identifier of the data manager review
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is authorized. If not, return PermissionError
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")
        isreviewer = datarequest_is_reviewer(ctx, request_id)

        if not (isboardmember or isdatamanager or isreviewer):
            log.write(ctx, "User is not authorized to view this data manager review.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to view this data manager review."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Construct filename
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'datamanager_review_datamanager.json'

    # Get the size of the data manager review JSON file and the review's status
    rows = row_iterator(["DATA_SIZE", "DATA_NAME", "COLL_NAME"],
                        "COLL_NAME = '%s' AND " % coll_name
                        + "DATA_NAME like '%s'" % file_name,
                        AS_DICT, ctx)
    for row in rows:
        coll_name = row['COLL_NAME']
        data_name = row['DATA_NAME']
        data_size = row['DATA_SIZE']

    # Construct path to file
    file_path = coll_name + '/' + data_name

    # Get the contents of the data manager review JSON file
    try:
        datamanager_review_json = data_object.read(ctx, file_path)
    except Exception:
        log.write(ctx, "Could not get data manager review data.")
        return {"status": "ReadError", "statusInfo": "Could not get data manager review data."}

    return datamanager_review_json


@api.make()
def api_datarequest_is_owner(ctx, request_id, user_name):
    result = datarequest_is_owner(ctx, request_id, user_name)

    if not (result['status'] == 0):
        return api.Error("error", "Something went wrong in determining datarequest ownership")

    return result['owner']


def datarequest_is_owner(ctx, request_id, user_name):
    """Check if the invoking user is also the owner of a given data request

       Arguments:
       request_id -- Unique identifier of the data request
       user_name  -- Username of the user whose ownership is checked

       Return:
       dict       -- status: 0 == lookup success, 1 == lookup fail
                     owner: True/False
    """
    # Construct path to the collection of the datarequest
    client_zone = user.zone(ctx)
    coll_path = ("/" + client_zone + "/home/datarequests-research/" + request_id)

    # Query iCAT for the username of the owner of the data request
    rows = row_iterator(["DATA_OWNER_NAME"],
                        ("DATA_NAME = 'datarequest.json' and COLL_NAME like " + "'%s'" % coll_path),
                        AS_DICT, ctx)

    # Extract username from query results
    request_owner_user_name = []
    for row in rows:
        request_owner_user_name.append(row["DATA_OWNER_NAME"])

    # Check if exactly 1 owner was found
    if len(request_owner_user_name) == 1:
        # We only have 1 owner. Set request_owner_user_name to this owner
        request_owner_user_name = request_owner_user_name[0]

        # Compare the request owner username to the username of the current
        # user to determine ownership
        is_request_owner = request_owner_user_name == user_name

        # Return data
        return {'owner': is_request_owner, 'status': 0}
    # If not exactly 1 owner was found, something went quite wrong. Return error
    else:
        return {'owner': None, 'status': 1}


@api.make()
def api_datarequest_is_reviewer(ctx, request_id):
    return datarequest_is_reviewer(ctx, request_id)


def datarequest_is_reviewer(ctx, request_id):
    """Check if a user is assigned as reviewer to a data request

       Arguments:
       request_id -- Unique identifier of the data request

       Return:
       dict       -- A JSON dict specifying whether the user is assigned as
                     reviewer to the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Get username
    username = user.name(ctx)

    # Reviewers are stored in one or more assignedForReview attributes on
    # the data request, so our first step is to query the metadata of our
    # data request file for these attributes

    # Declare variables needed for retrieving the list of reviewers
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'datarequest.json'
    reviewers = []

    # Retrieve list of reviewers
    rows = row_iterator(["META_DATA_ATTR_VALUE"],
                        "COLL_NAME = '%s' AND " % coll_name
                        + "DATA_NAME = '%s' AND " % file_name
                        + "META_DATA_ATTR_NAME = 'assignedForReview'",
                        AS_DICT, ctx)
    for row in rows:
        reviewers.append(row['META_DATA_ATTR_VALUE'])

    # Check if the reviewers list contains the current user
    is_reviewer = username in reviewers

    # Return the is_reviewer boolean
    return is_reviewer


@api.make()
def api_datarequest_assignment_submit(ctx, data, request_id):
    """Persist an assignment to disk.

       Arguments:
       data       -- Contents of the assignment
       request_id -- Unique identifier of the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Read assignment into dictionary
    assignment = json.loads(data)

    # Check if user is a member of the Board of Directors. If not, do not
    # allow assignment
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")

        if not isboardmember:
            log.write(ctx, "User is not a member of the Board of Directors.")
            return {"status": "PermissionError", "statusInfo": "User is not a member of the Board of Directors"}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Check if status is appropriate for assignment
    if not get_status(ctx, request_id) in ['dm_accepted', 'dm_rejected', 'dm_rejected_resubmit']:
        log.write(ctx, "Current status of data request does not permit this operation.")
        return {"status": "PermissionError", "statusInfo": "Current status of data request does not permit this operation."}

    # Construct path to collection of the evaluation
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    # Get username
    client_name = user.name(ctx)

    # Write assignment data to disk
    try:
        assignment_path = coll_path + '/assignment_' + client_name + '.json'
        jsonutil.write(ctx, assignment_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write assignment data to disk')

    # Give read permission on the assignment to data managers and Board of Directors members
    try:
        msi.set_acl(ctx, "default", "read", "datarequests-research-board-of-directors", assignment_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-datamanagers", assignment_path)
        msi.set_acl(ctx, "default", "read", "datarequests-research-data-management-committee", assignment_path)
    except Exception:
        log.write(ctx, "Could not grant read permissions on the assignment file.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the assignment file."}

    # Get the outcome of the assignment (accepted/rejected)
    decision = assignment['decision']

    # If the data request has been accepted for DMC review, get the assignees
    assignees = json.dumps(assignment['assign_to'])

    # Update the status of the data request
    if decision == "Accepted for DMC review":
        assign_request(ctx, assignees, request_id)
        set_status(ctx, request_id, "assigned")
    elif decision == "Rejected":
        set_status(ctx, request_id, "rejected_after_data_manager_review")
    elif decision == "Rejected (resubmit)":
        set_status(ctx, request_id, "rejected_resubmit_after_data_manager_review")
    else:
        log.write(ctx, "Invalid value for 'decision' key in datamanager review JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'decision' key in datamanager review JSON data."}

    # Get email parameters
    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    contact = datarequest['researchers']['contacts'][0]

    researcher_name  = contact['name']
    researcher_email = contact['email']
    proposal_title   = datarequest['research_context']['title']

    if 'feedback_for_researcher' in assignment:
        feedback_for_researcher = assignment['feedback_for_researcher']

    # Send emails to the researcher (and to the assignees if the data request has been accepted for DMC review)
    if decision == "Accepted for DMC review":
        mail_assignment_researcher(ctx, decision, researcher_email, researcher_name, request_id)
        for assignee_email in json.loads(assignees):
            mail_assignment_assignee(ctx, assignee_email, proposal_title, request_id)
    else:
        mail_assignment_researcher(ctx, decision, researcher_email, researcher_name, request_id,
                                   feedback_for_researcher)


def assign_request(ctx, assignees, request_id):
    """Assign a data request to one or more DMC members for review.

       Arguments:
       assignees -- JSON-formatted array of DMC members.
       request_id -- Unique identifier of the data request

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    # Check if user is a data manager. If not, do not the user to assign the
    # request
    try:
        isbodmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")

        if not isbodmember:
            raise Exception
    except Exception:
        log.write(ctx, "User is not a data manager.")
        return {"status": "PermissionDenied", "statusInfo": "User is not a data manager."}

    # Construct data request collection path
    requestColl = ('/tempZone/home/datarequests-research/' + request_id)

    # Check if data request has already been assigned. If true, set status
    # code to failure and do not perform requested assignment
    rows = row_iterator(["META_DATA_ATTR_VALUE"],
                        "COLL_NAME = '%s' AND " % requestColl
                        + "DATA_NAME = 'datarequest.json' AND "
                        + "META_DATA_ATTR_NAME = 'status'",
                        AS_DICT, ctx)

    for row in rows:
        requestStatus = row['META_DATA_ATTR_VALUE']

    if not (requestStatus == "dm_accepted" or requestStatus == "dm_rejected"):
        log.write(ctx, "Proposal is already assigned.")
        return {"status": "AlreadyAssigned", "statusInfo": "Proposal is already assigned."}

    # Assign the data request by adding a delayed rule that sets one or more
    # "assignedForReview" attributes on the datarequest (the number of
    # attributes is determined by the number of assignees) ...
    status = ""
    status_info = ""
    ctx.requestDatarequestMetadataChange(requestColl,
                                         "assignedForReview",
                                         assignees,
                                         str(len(json.loads(assignees))),
                                         status, status_info)

    # ... and triggering the processing of delayed rules
    ctx.adminDatarequestActions()


@api.make()
def api_datarequest_assignment_get(ctx, request_id):
    """Retrieve assignment.

       Arguments:
       request_id -- Unique identifier of the assignment
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'assignment_bodmember.json'

    # Get the size of the assignment JSON file and the review's status
    rows = row_iterator(["DATA_NAME", "COLL_NAME"],
                        "COLL_NAME = '%s' AND " % coll_name
                        + "DATA_NAME like '%s'" % file_name,
                        AS_DICT, ctx)
    for row in rows:
        coll_name = row['COLL_NAME']
        data_name = row['DATA_NAME']

    # Construct path to file
    file_path = coll_name + '/' + data_name

    # Get the contents of the assignment JSON file
    try:
        assignment_json = data_object.read(ctx, file_path)
    except Exception:
        log.write(ctx, "Could not get assignment data.")
        return {"status": "ReadError", "statusInfo": "Could not get assignment data."}

    return assignment_json


@api.make()
def api_datarequest_review_submit(ctx, data, request_id):
    """Persist a data request review to disk.

       Arguments:
       data -- JSON-formatted contents of the data request review
       proposalId -- Unique identifier of the research proposal

       Return:
       dict -- A JSON dict with status info for the front office.
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is a member of the Data Management Committee. If not, do
    # not allow submission of the review
    try:
        isreviewer = datarequest_is_reviewer(ctx, request_id)

        if not isreviewer:
            log.write(ctx, "User is assigned as a reviewer to this data request.")
            return {"status": "PermissionError", "statusInfo": "User is not assigned as a reviewer to this data request."}
    except Exception:
        log.write(ctx, "User is not a member of the Board of Directors.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Check if status is appropriate for submission of the review
    if not get_status(ctx, request_id) == 'assigned':
        log.write(ctx, "Current status of data request does not permit this operation.")
        return {"status": "PermissionError", "statusInfo": "Current status of data request does not permit this operation."}

    # Check if the user has been assigned as a reviewer. If not, do not
    # allow submission of the review
    try:
        isreviewer = datarequest_is_reviewer(ctx, request_id)

        if not isreviewer:
            raise Exception
    except Exception:
        log.write(ctx, "User is not assigned as a reviewer to this request.")
        return {"status": "PermissionDenied", "statusInfo": "User is not assigned as a reviewer to this request."}

    # Construct path to collection of review
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    # Get username
    client_name = user.name(ctx)

    # Write review data to disk
    try:
        review_path = coll_path + '/review_' + client_name + '.json'
        jsonutil.write(ctx, review_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write review data to disk')

    # Give read permission on the review to Board of Director members
    try:
        msi.set_acl(ctx, "default", "read", "datarequests-research-board-of-directors", review_path)
    except Exception:
        log.write(ctx, "Could not grant read permissions on the review file to the Board of Directors.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the review file to the Board of Directors"}

    # Remove the assignedForReview attribute of this user by first fetching
    # the list of reviewers ...
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'datarequest.json'
    reviewers = []
    client_zone = user.zone(ctx)

    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME = '%s' AND " % coll_name
        + "DATA_NAME = 'datarequest.json' AND "
        + "META_DATA_ATTR_NAME = 'assignedForReview'",
        genquery.AS_LIST, ctx)

    for row in iter:
        reviewer = row[0]
        reviewers.append(reviewer)

    # ... then removing the current reviewer from the list
    reviewers.remove(client_name)

    # ... and then updating the assignedForReview attributes
    status = ""
    status_info = ""
    ctx.requestDatarequestMetadataChange(coll_name,
                                         "assignedForReview",
                                         json.dumps(reviewers),
                                         str(len(reviewers)),
                                         status, status_info)
    ctx.adminDatarequestActions()

    # If there are no reviewers left, change the status of the proposal to
    # 'reviewed' and send an email to the board of directors members
    # informing them that the proposal is ready to be evaluated by them.
    if len(reviewers) < 1:
        set_status(ctx, request_id, "reviewed")

        # Get parameters needed for sending emails
        datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

        researcher = datarequest['researchers']['contacts'][0]

        researcher_name = researcher['name']
        researcher_email = researcher['email']

        bod_member_emails = json.loads(ctx.uuGroupGetMembersAsJson(
                                       'datarequests-research-board-of-directors',
                                       "")['arguments'][1])

        # Send email to researcher and data manager notifying them of the
        # submission of this data request
        mail_review_researcher(ctx, researcher_email, researcher_name, request_id)
        for bodmember_email in bod_member_emails:
            if not bodmember_email == "rods":
                mail_review_bodmember(ctx, bodmember_email, request_id)


@api.make()
def api_datarequest_reviews_get(ctx, request_id):
    """Retrieve a data request review.

       Arguments:
       request_id -- Unique identifier of the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is authorized. If not, return PermissionError
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")

        if not isboardmember:
            log.write(ctx, "User is not authorized to view this review.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to view this review."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Construct filename
    coll_name = '/tempZone/home/datarequests-research/' + request_id
    file_name = 'review_%.json'

    # Get the review JSON files
    reviews = []
    rows = row_iterator(["DATA_NAME"],
                        "COLL_NAME = '%s' AND " % coll_name
                        + "DATA_NAME like '%s'" % file_name,
                        AS_DICT, ctx)
    for row in rows:
        file_path = coll_name + '/' + row['DATA_NAME']
        try:
            reviews.append(json.loads(data_object.read(ctx, file_path)))
        except Exception:
            log.write(ctx, "Could not get review data.")
            return {"status": "ReadError", "statusInfo": "Could not get review data."}

    return json.dumps(reviews)


@api.make()
def api_datarequest_evaluation_submit(ctx, data, request_id):
    """Persist an evaluation to disk.

       Arguments:
       data       -- Contents of the evaluation
       proposalId -- Unique identifier of the research proposal
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is a member of the Board of Directors. If not, do not
    # allow submission of the evaluation
    try:
        isboardmember = user.is_member_of(ctx, "datarequests-research-board-of-directors")

        if not isboardmember:
            log.write(ctx, "User is not a member of the Board of Directors.")
            return {"status": "PermissionError", "statusInfo": "User is not a member of the Board of Directors"}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Check if status is appropriate for submission of the evaluation
    if not get_status(ctx, request_id) == 'reviewed':
        log.write(ctx, "Current status of data request does not permit this operation.")
        return {"status": "PermissionError", "statusInfo": "Current status of data request does not permit this operation."}

    # Construct path to collection of the evaluation
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    # Get username
    client_name = user.name(ctx)

    # Write evaluation data to disk
    try:
        evaluation_path = coll_path + '/evaluation_' + client_name + '.json'
        jsonutil.write(ctx, evaluation_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write evaluation data to disk')

    # Get outcome of evaluation
    decision = json.loads(data)['evaluation']

    # Update the status of the data request
    if decision == "Approved":
        set_status(ctx, request_id, "approved")
    elif decision == "Rejected":
        set_status(ctx, request_id, "rejected")
    elif decision == "Rejected (resubmit)":
        set_status(ctx, request_id, "rejected_resubmit")
    else:
        log.write(ctx, "Invalid value for 'evaluation' key in evaluation JSON data.")
        return {"status": "InvalidData", "statusInfo": "Invalid value for 'evaluation' key in evaluation JSON data."}

    # Get parameters needed for sending emails
    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    researcher = datarequest['researchers']['contacts'][0]

    researcher_name = researcher['name']
    researcher_email = researcher['email']

    datamanager_emails = json.loads(ctx.uuGroupGetMembersAsJson(
                                    'datarequests-research-datamanagers', "")['arguments'][1])

    # Send an email to the researcher informing them of whether their data
    # request has been approved or rejected.
    if decision == "Approved":
        mail_evaluation_researcher(ctx, decision, researcher_email, researcher_name, request_id)
        for datamanager_email in datamanager_emails:
            if not datamanager_email == "rods":
                mail_evaluation_datamanager(ctx, datamanager_email, request_id)
    else:
        mail_evaluation_researcher(ctx, decision, researcher_email, researcher_name, request_id,
                                   datamanager_emails[0], feedback_for_researcher)


@api.make()
def api_datarequest_dta_post_upload_actions(ctx, request_id):
    """Grant read permissions on the DTA to the owner of the associated data request.

       Arguments:
       requestId --
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is allowed to view to proposal. If not, return
    # PermissionError
    try:
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")

        if not isdatamanager:
            log.write(ctx, "User is not authorized to grant read permissions on the DTA.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to grant read permissions on the DTA."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Construct path to the collection of the datarequest
    client_zone = user.zone(ctx)
    coll_path = ("/" + client_zone + "/home/datarequests-research/"
                 + request_id)

    # Query iCAT for the username of the owner of the data request
    rows = row_iterator(["DATA_OWNER_NAME"],
                        ("DATA_NAME = 'datarequest.json' and COLL_NAME like " + "'%s'" % coll_path),
                        AS_DICT, ctx)

    # Extract username from query results
    request_owner_username = []
    for row in rows:
        request_owner_username.append(row["DATA_OWNER_NAME"])

    # Check if exactly 1 owner was found. If not, wipe
    # requestOwnerUserName list and set error status code
    if len(request_owner_username) != 1:
        log.write(ctx, "Not exactly 1 owner found. Something is very wrong.")
        return {"status": "MoreThanOneOwner", "statusInfo": "Not exactly 1 owner found. Something is very wrong."}

    request_owner_username = request_owner_username[0]

    try:
        msi.set_acl(ctx, "default", "read", request_owner_username, coll_path + "/dta.pdf")
    except Exception:
        log.write(ctx, "Could not grant read permissions on the DTA to the data request owner.")
        return {"status": "PermissionError", "statusInfo": "Could not grant read permissions on the DTA to the data request owner."}

    # Set status to dta_ready
    set_status(ctx, request_id, "dta_ready")

    # Get parameters needed for sending emails
    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    researcher = datarequest['researchers']['contacts'][0]

    researcher_name = researcher['name']
    researcher_email = researcher['email']

    # Send an email to the researcher informing them that the DTA of their
    # data request is ready for them to sign and upload
    mail_dta(ctx, researcher_email, researcher_name, request_id)


@api.make()
def api_datarequest_signed_dta_post_upload_actions(ctx, request_id):
    """Grant read permissions on the signed DTA to the datamanagers group.

       Arguments:
       request_id -- Unique identifier of the datarequest.
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Check if user is allowed to view to proposal. If not, return
    # PermissionError
    try:
        isrequestowner = datarequest_is_owner(ctx, request_id, user.name(ctx))['owner']

        if not isrequestowner:
            log.write(ctx, "User is not authorized to grant read permissions on the signed DTA.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to grant read permissions on the signed DTA."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    # Construct path to the collection of the datarequest
    client_zone = user.zone(ctx)
    coll_path = ("/" + client_zone + "/home/datarequests-research/" + request_id)

    try:
        msi.set_acl(ctx, "default", "read", "datarequests-research-datamanagers", coll_path + "/signed_dta.pdf")
    except Exception:
        log.write(ctx, "Could not grant read permissions on the signed DTA to the data managers group.")
        return {"status": "PermissionsError", "statusInfo": "Could not grant read permissions on the signed DTA to the data managers group."}

    # Set status to dta_signed
    set_status(ctx, request_id, "dta_signed")

    # Get parameters needed for sending emails
    datamanager_emails = ""
    datamanager_emails = json.loads(ctx.uuGroupGetMembersAsJson('datarequests-research-datamanagers', datamanager_emails)['arguments'][1])

    # Send an email to the data manager informing them that the DTA has been
    # signed by the researcher
    for datamanager_email in datamanager_emails:
        if not datamanager_email == "rods":
            mail_signed_dta(ctx, datamanager_email, request_id)


@api.make()
def api_datarequest_data_ready(ctx, request_id):
    """Set the status of a submitted datarequest to "Data ready".

       Arguments:
       request_id        -- Unique identifier of the datarequest.
    """
    # Check if user is allowed to view to proposal. If not, return
    # PermissionError
    try:
        isdatamanager = user.is_member_of(ctx, "datarequests-research-datamanagers")

        if not isdatamanager:
            log.write(ctx, "User is not authorized to mark the data as ready.")
            return {'status': "PermissionError", 'statusInfo': "User is not authorized to mark the data as ready."}
    except Exception:
        log.write(ctx, "Something went wrong during permission checking.")
        return {'status': "PermissionError", 'statusInfo': "Something went wrong during permission checking."}

    set_status(ctx, request_id, "data_ready")

    # Get parameters needed for sending emails
    zone_path = '/tempZone/home/datarequests-research/'
    coll_path = zone_path + request_id

    datarequest = jsonutil.read(ctx, coll_path + "/datarequest.json")

    researcher = datarequest['researchers']['contacts'][0]

    researcher_name = researcher['name']
    researcher_email = researcher['email']

    # Send email to researcher notifying him of of the submission of his
    # request
    mail_data_ready(ctx, researcher_email, researcher_name, request_id)


def mail_datarequest_researcher(ctx, researcher_email, researcher_name, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = '[researcher] YOUth data request {}: submitted'.format(request_id),
                     body    = """
Dear {},

Your data request has been submitted.

You will be notified by email of the status of your request. You may also log into Yoda to view the status and other information about your data request.

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, request_id))


def mail_datarequest_bodmember(ctx, bodmember_email, request_id, researcher_name, researcher_email,
                               researcher_institution, researcher_department, submission_date,
                               proposal_title):
    return mail.send(ctx,
                     to      = bodmember_email,
                     actor   = user.full_name(ctx),
                     subject = "[bodmember] YOUth data request {}: submitted".format(request_id),
                     body    = """
Dear board of directors member,

A new data request has been submitted.

Submitted by: {} ({})
Affiliation: {}, {}
Date: {}
Request ID: {}
Proposal title: {}

The following link will take you to the preliminary review form: https://portal.yoda.test/datarequest/preliminaryreview/{}.

With kind regards,
YOUth
""".format(researcher_name, researcher_email, researcher_institution, researcher_department, submission_date, request_id, proposal_title, request_id))


def mail_preliminary_review_accepted(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to      = datamanager_email,
                     actor   = user.full_name(ctx),
                     subject = "[data manager] YOUth data request {}: accepted for data manager review".format(request_id),
                     body    = """
Dear data manager,

Data request {} has been approved for review by the Board of Directors.

You are now asked to review the data request for any potential problems concerning the requested data.

The following link will take you directly to the review form: https://portal.yoda.test/datarequest/datamanagerreview/{}.

With kind regards,
YOUth
""".format(request_id, request_id))


def mail_preliminary_review_resubmit(ctx, researcher_email, researcher_name,
                                     feedback_for_researcher, datamanager_email, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = "[researcher] YOUth data request {}: rejected (resubmit)".format(request_id),
                     body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

You are however allowed to resubmit your data request. To do so, follow the following link: https://portal.yoda.test/datarequest/add/{}.

If you wish to object against this rejection, please contact the YOUth data manager ({}).

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, request_id, datamanager_email))


def mail_preliminary_review_rejected(ctx, researcher_email, researcher_name,
                                     feedback_for_researcher, datamanager_email, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = "[researcher] YOUth data request {}: rejected".format(request_id),
                     body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

If you wish to object against this rejection, please contact the YOUth data manager ({}).

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, datamanager_email))


def mail_datamanager_review_accepted(ctx, bodmember_email, request_id):
    return mail.send(ctx,
                     to      = bodmember_email,
                     actor   = user.full_name(ctx),
                     subject = "[bod member] YOUth data request {}: accepted by data manager".format(request_id),
                     body    = """
Dear executive board delegate,

Data request {} has been accepted by the data manager.

You are now asked to assign the data request for review to one or more DMC members. To do so, please navigate to the assignment form using this link: https://portal.yoda.test/datarequest/assign/{}.

With kind regards,
YOUth
""".format(request_id, request_id))


def mail_datamanager_review_resubmit(ctx, bodmember_email, datamanager_remarks, request_id):
    return mail.send(ctx,
                     to      = bodmember_email,
                     actor   = user.full_name(ctx),
                     subject = "[bod member] YOUth data request {}: rejected (resubmit) by data manager".format(request_id),
                     body    = """
Dear executive board delegate,

Data request {} has been rejected (resubmission allowed) by the data manager for the following reason(s):

{}

The data manager's review is advisory. Please consider the objections raised and then either reject the data request or assign it for review to one or more DMC members. To do so, please navigate to the assignment form using this link https://portal.yoda.test/datarequest/assign/{}.

With kind regards,
YOUth
""".format(request_id, datamanager_remarks, request_id))


def mail_datamanager_review_rejected(ctx, bodmember_email, datamanager_remarks, request_id):
    return mail.send(ctx,
                     to      = bodmember_email,
                     actor   = user.full_name(ctx),
                     subject = "[bod member] YOUth data request {}: rejected by data manager".format(request_id),
                     body    = """
Dear executive board delegate,

Data request {} has been rejected by the data manager for the following reason(s):

{}

The data manager's review is advisory. Please consider the objections raised and then either reject the data request or assign it for review to one or more DMC members. To do so, please navigate to the assignment form using this link https://portal.yoda.test/datarequest/assign/{}.

With kind regards,
YOUth
""".format(request_id, datamanager_remarks, request_id))


def mail_assignment_researcher(ctx, decision, researcher_email, researcher_name, request_id,
                               feedback_for_researcher = None):

    if decision == "Accepted for DMC review":
        subject = "[researcher] YOUth data request {}: assigned".format(request_id)
        body    = """
Dear {},

Your data request has been assigned for review by the YOUth data manager.

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, request_id)
    elif decision == "Rejected (resubmit)":
        subject = "[researcher] YOUth data request {}: rejected (resubmit)".format(request_id)
        body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

You are however allowed to resubmit your data request. To do so, follow the following link: https://portal.yoda.test/datarequest/add/{}.

If you wish to object against this rejection, please contact the YOUth data manager.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, request_id)
    elif decision == "Rejected":
        subject = "[researcher] YOUth data request {}: rejected".format(request_id)
        body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

If you wish to object against this rejection, please contact the YOUth data manager.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher)

    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = subject,
                     body    = body)


def mail_assignment_assignee(ctx, assignee_email, proposal_title, request_id):
    return mail.send(ctx,
                     to      = assignee_email,
                     actor   = user.full_name(ctx),
                     subject = "[assignee] YOUth data request {}: assigned".format(request_id),
                     body    = """
Dear DMC member,

Data request {} (proposal title: \"{}\") has been assigned to you for review. Please sign in to Yoda to view the data request and submit your review.

The following link will take you directly to the review form: https://portal.yoda.test/datarequest/review/{}.

With kind regards,
YOUth
""".format(request_id, proposal_title, request_id))


def mail_review_researcher(ctx, researcher_email, researcher_name, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = "[researcher] YOUth data request {}: reviewed".format(request_id),
                     body    = """
Dear {},

Your data request been reviewed by the YOUth data management committee and is awaiting final evaluation by the YOUth Board of Directors.

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, request_id))


def mail_review_bodmember(ctx, bodmember_email, request_id):
    return mail.send(ctx,
                     to      = bodmember_email,
                     actor   = user.full_name(ctx),
                     subject = "[bod member] YOUth data request {}: reviewed".format(request_id),
                     body    = """
Dear Board of Directors member,

Data request {} has been reviewed by the YOUth data management committee and is awaiting your final evaluation.

Please log into Yoda to evaluate the data request.

The following link will take you directly to the evaluation form: https://portal.yoda.test/datarequest/evaluate/{}.

With kind regards,
YOUth
""".format(request_id, request_id))


def mail_evaluation_researcher(ctx, decision, researcher_email, researcher_name, request_id,
                               datamanager_email = None, feedback_for_researcher = None):
    if decision == "Approved":
        subject = "[researcher] YOUth data request {}: approved".format(request_id)
        body    = """
Dear {},

Congratulations! Your data request has been approved. The YOUth data manager will now create a Data Transfer Agreement for you to sign. You will be notified when it is ready.

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, request_id)
    elif decision == "Rejected (resubmit)":
        subject = "[researcher] YOUth data request {}: rejected".format(request_id)
        body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

You are however allowed to resubmit your data request. To do so, follow the following link: https://portal.yoda.test/datarequest/add/{}.

If you wish to object against this rejection, please contact the YOUth data manager ({}).

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, request_id, datamanager_email, request_id)
    elif decision == "Rejected":
        subject = "[researcher] YOUth data request {}: rejected (resubmit)".format(request_id)
        body    = """
Dear {},

Your data request has been rejected for the following reason(s):

{}

If you wish to object against this rejection, please contact the YOUth data manager ({}).

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, datamanager_email, request_id)

    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = subject,
                     body    = body)


def mail_evaluation_datamanager(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to      = datamanager_email,
                     actor   = user.full_name(ctx),
                     subject = "[data manager] YOUth data request {}: approved".format(request_id),
                     body    = """
Dear data manager,

Data request {} has been approved by the Board of Directors. Please sign in to Yoda to upload a Data Transfer Agreement for the researcher.

The following link will take you directly to the data request: https://portal.yoda.test/datarequest/view/{}.

With kind regards,
YOUth
""".format(request_id, request_id))


def mail_dta(ctx, researcher_email, researcher_name, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = "[researcher] YOUth data request {}: DTA ready".format(request_id),
                     body    = """
Dear {},

The YOUth data manager has created a Data Transfer Agreement to formalize the transfer of the data you have requested. Please sign in to Yoda to download and read the Data Transfer Agreement.

The following link will take you directly to your data request: https://portal.yoda.test/datarequest/view/{}.

If you do not object to the agreement, please upload a signed copy of the agreement. After this, the YOUth data manager will prepare the requested data and will provide you with instructions on how to download them.

With kind regards,
YOUth
""".format(researcher_name, request_id))


def mail_signed_dta(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to      = datamanager_email,
                     actor   = user.full_name(ctx),
                     subject = "[data manager] YOUth data request {}: DTA signed".format(request_id),
                     body    = """
Dear data manager,

The researcher has uploaded a signed copy of the Data Transfer Agreement for data request {}.

Please log in to Yoda to review this copy. The following link will take you directly to the data request: https://portal.yoda.test/datarequest/view/{}.

After verifying that the document has been signed correctly, you may prepare the data for download. When the data is ready for the researcher to download, please click the \"Data ready\" button. This will notify the researcher by email that the requested data is ready. The email will include instructions on downloading the data.

With kind regards,
YOUth
""".format(request_id, request_id))


def mail_data_ready(ctx, researcher_email, researcher_name, request_id):
    return mail.send(ctx,
                     to      = researcher_email,
                     actor   = user.full_name(ctx),
                     subject = "[researcher] YOUth data request {}: Data ready".format(request_id),
                     body    = """
Dear {},

The data you have requested is ready for you to download! [instructions here].

With kind regards,
YOUth
""".format(researcher_name))
