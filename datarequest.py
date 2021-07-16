# -*- coding: utf-8 -*-
"""Functions to handle data requests."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'
__author__    = ('Lazlo Westerhof, Jelmer Zondergeld')

import json
import re
from collections import OrderedDict
from datetime import datetime
from enum import Enum

import jsonschema
from genquery import AS_DICT, row_iterator

import avu_json
import mail
from util import *
from util.query import Query

__all__ = ['api_datarequest_roles_get',
           'api_datarequest_action_permitted',
           'api_datarequest_browse',
           'api_datarequest_schema_get',
           'api_datarequest_submit',
           'api_datarequest_get',
           'api_datarequest_attachment_upload_permission',
           'api_datarequest_attachment_post_upload_actions',
           'api_datarequest_attachments_get',
           'api_datarequest_attachments_submit',
           'api_datarequest_preliminary_review_submit',
           'api_datarequest_preliminary_review_get',
           'api_datarequest_datamanager_review_submit',
           'api_datarequest_datamanager_review_get',
           'api_datarequest_dmr_review_submit',
           'api_datarequest_dmr_review_get',
           'api_datarequest_contribution_review_submit',
           'api_datarequest_contribution_review_get',
           'api_datarequest_assignment_submit',
           'api_datarequest_assignment_get',
           'api_datarequest_review_submit',
           'api_datarequest_reviews_get',
           'api_datarequest_evaluation_submit',
           'api_datarequest_feedback_get',
           'api_datarequest_contribution_confirm',
           'api_datarequest_dta_upload_permission',
           'api_datarequest_dta_post_upload_actions',
           'api_datarequest_dta_path_get',
           'api_datarequest_signed_dta_upload_permission',
           'api_datarequest_signed_dta_post_upload_actions',
           'api_datarequest_signed_dta_path_get',
           'api_datarequest_data_ready']


###################################################
#                    Constants                    #
###################################################

DATAREQUESTSTATUSATTRNAME = "status"

YODA_PORTAL_FQDN  = config.yoda_portal_fqdn

JSON_EXT          = ".json"

SCHEMACOLLECTION  = constants.UUSYSTEMCOLLECTION + "/datarequest/schemas/youth-0"
SCHEMA            = "schema"
UISCHEMA          = "uischema"

GROUP_DM          = "datarequests-research-datamanagers"
GROUP_DMC         = "datarequests-research-data-management-committee"
GROUP_PM          = "datarequests-research-project-managers"
GROUP_ED          = "datarequests-research-executive-directors"

DRCOLLECTION         = "home/datarequests-research"
PROVENANCE           = "provenance"
DATAREQUEST          = "datarequest"
ATTACHMENTS_PATHNAME = "attachments"
PR_REVIEW            = "preliminary_review"
DM_REVIEW            = "datamanager_review"
DMR_REVIEW           = "dmr_review"
CONTRIB_REVIEW       = "contribution_review"
REVIEW               = "review"
ASSIGNMENT           = "assignment"
EVALUATION           = "evaluation"
FEEDBACK             = "feedback"
DTA_PATHNAME         = "dta"
SIGDTA_PATHNAME      = "signed_dta"


###################################################
#          Datarequest status functions           #
###################################################

# List of valid datarequest statuses
class status(Enum):
    IN_SUBMISSION                     = 'IN_SUBMISSION'

    DRAFT                             = 'DRAFT'

    DAO_SUBMITTED                     = 'DAO_SUBMITTED'
    PENDING_ATTACHMENTS               = 'PENDING_ATTACHMENTS'
    SUBMITTED                         = 'SUBMITTED'

    PRELIMINARY_ACCEPT                = 'PRELIMINARY_ACCEPT'
    PRELIMINARY_REJECT                = 'PRELIMINARY_REJECT'
    PRELIMINARY_RESUBMIT              = 'PRELIMINARY_RESUBMIT'

    DATAMANAGER_ACCEPT                = 'DATAMANAGER_ACCEPT'
    DATAMANAGER_REJECT                = 'DATAMANAGER_REJECT'
    DATAMANAGER_RESUBMIT              = 'DATAMANAGER_RESUBMIT'

    DATAMANAGER_REVIEW_ACCEPTED       = 'DATAMANAGER_REVIEW_ACCEPTED'
    REJECTED_AFTER_DATAMANAGER_REVIEW = 'REJECTED_AFTER_DATAMANAGER_REVIEW'
    RESUBMIT_AFTER_DATAMANAGER_REVIEW = 'RESUBMIT_AFTER_DATAMANAGER_REVIEW'

    CONTRIBUTION_ACCEPTED             = 'CONTRIBUTION_ACCEPTED'
    CONTRIBUTION_REJECTED             = 'CONTRIBUTION_REJECTED'
    CONTRIBUTION_RESUBMIT             = 'CONTRIBUTION_RESUBMIT'

    UNDER_REVIEW                      = 'UNDER_REVIEW'

    REVIEWED                          = 'REVIEWED'

    APPROVED                          = 'APPROVED'
    REJECTED                          = 'REJECTED'
    RESUBMIT                          = 'RESUBMIT'

    CONTRIBUTION_CONFIRMED            = 'CONTRIBUTION_CONFIRMED'
    DAO_APPROVED                      = 'DAO_APPROVED'

    DTA_READY                         = 'DTA_READY'
    DTA_SIGNED                        = 'DTA_SIGNED'
    DATA_READY                        = 'DATA_READY'


# List of valid datarequest status transitions (source, destination)
status_transitions = [(status(x),
                       status(y))
                      for x, y in [('IN_SUBMISSION',               'DRAFT'),
                                   ('IN_SUBMISSION',               'PENDING_ATTACHMENTS'),
                                   ('IN_SUBMISSION',               'DAO_SUBMITTED'),
                                   ('IN_SUBMISSION',               'SUBMITTED'),

                                   ('DRAFT',                       'PENDING_ATTACHMENTS'),
                                   ('DRAFT',                       'DAO_SUBMITTED'),
                                   ('DRAFT',                       'SUBMITTED'),

                                   ('PENDING_ATTACHMENTS',         'SUBMITTED'),

                                   ('DAO_SUBMITTED',               'DAO_APPROVED'),
                                   ('DAO_SUBMITTED',               'REJECTED'),
                                   ('DAO_SUBMITTED',               'RESUBMIT'),

                                   ('SUBMITTED',                   'PRELIMINARY_ACCEPT'),
                                   ('SUBMITTED',                   'PRELIMINARY_REJECT'),
                                   ('SUBMITTED',                   'PRELIMINARY_RESUBMIT'),

                                   ('PRELIMINARY_ACCEPT',          'DATAMANAGER_ACCEPT'),
                                   ('PRELIMINARY_ACCEPT',          'DATAMANAGER_REJECT'),
                                   ('PRELIMINARY_ACCEPT',          'DATAMANAGER_RESUBMIT'),

                                   ('DATAMANAGER_ACCEPT',          'DATAMANAGER_REVIEW_ACCEPTED'),
                                   ('DATAMANAGER_ACCEPT',          'REJECTED_AFTER_DATAMANAGER_REVIEW'),
                                   ('DATAMANAGER_ACCEPT',          'RESUBMIT_AFTER_DATAMANAGER_REVIEW'),
                                   ('DATAMANAGER_REJECT',          'DATAMANAGER_REVIEW_ACCEPTED'),
                                   ('DATAMANAGER_REJECT',          'REJECTED_AFTER_DATAMANAGER_REVIEW'),
                                   ('DATAMANAGER_REJECT',          'RESUBMIT_AFTER_DATAMANAGER_REVIEW'),
                                   ('DATAMANAGER_RESUBMIT',        'DATAMANAGER_REVIEW_ACCEPTED'),
                                   ('DATAMANAGER_RESUBMIT',        'REJECTED_AFTER_DATAMANAGER_REVIEW'),
                                   ('DATAMANAGER_RESUBMIT',        'RESUBMIT_AFTER_DATAMANAGER_REVIEW'),

                                   ('DATAMANAGER_REVIEW_ACCEPTED', 'CONTRIBUTION_ACCEPTED'),
                                   ('DATAMANAGER_REVIEW_ACCEPTED', 'CONTRIBUTION_REJECTED'),
                                   ('DATAMANAGER_REVIEW_ACCEPTED', 'CONTRIBUTION_RESUBMIT'),

                                   ('CONTRIBUTION_ACCEPTED',       'UNDER_REVIEW'),

                                   ('UNDER_REVIEW',                'REVIEWED'),

                                   ('REVIEWED',                    'APPROVED'),
                                   ('REVIEWED',                    'REJECTED'),
                                   ('REVIEWED',                    'RESUBMIT'),

                                   ('APPROVED',                    'CONTRIBUTION_CONFIRMED'),

                                   ('CONTRIBUTION_CONFIRMED',      'DTA_READY'),
                                   ('DAO_APPROVED',                'DTA_READY'),

                                   ('DTA_READY',                   'DTA_SIGNED'),

                                   ('DTA_SIGNED',                  'DATA_READY')]]


def status_transition_allowed(ctx, current_status, new_status):
    transition = (current_status, new_status)

    return transition in status_transitions


def status_set(ctx, request_id, status):
    """Set the status of a data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param status:     The status to which the data request should be set
    """
    metadata_set(ctx, request_id, "status", status.value)


def status_get_from_path(ctx, path):
    """Get the status of a datarequest from a path

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of the datarequest collection

    :returns: Status of given data request
    """
    temp, _ = pathutil.chop(path)
    _, request_id = pathutil.chop(temp)

    return status_get(ctx, request_id)


def status_get(ctx, request_id):
    """Get the status of a data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :raises UUError: Status could not be retrieved

    :returns: Status of given data request
    """
    # Construct filename and filepath
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = DATAREQUEST + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Retrieve current status
    rows = row_iterator(["META_DATA_ATTR_VALUE"],
                        ("COLL_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = 'status'").format(coll_path, file_name),
                        AS_DICT, ctx)
    if rows.total_rows() == 1:
        return status[list(rows)[0]['META_DATA_ATTR_VALUE']]
    # If no status is set, set status to IN_SUBMISSION (this is the case for newly submitted data
    # requests)
    elif rows.total_rows() == 0:
        return status.IN_SUBMISSION
    else:
        raise error.UUError("Could not unambiguously determine the current status for datarequest <{}>".format(request_id))


###################################################
#                 Helper functions                #
###################################################

def metadata_set(ctx, request_id, key, value):
    """Set an arbitrary metadata field on a data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param key:        Key of the metadata field
    :param value:      Value of the metadata field
    """

    # Construct path to the collection of the data request
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Add delayed rule to update data request status
    response_status = ""
    response_status_info = ""
    ctx.requestDatarequestMetadataChange(coll_path, key, value, "0", response_status,
                                         response_status_info)

    # Trigger the processing of delayed rules
    ctx.adminDatarequestActions()


@api.make()
def api_datarequest_action_permitted(ctx, request_id, roles, statuses):
    """Wrapper around datarequest_action_permitted

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :param roles:        Array of permitted roles (possible values: PM, ED, DM, DMC, OWN, REV)
    :param statuses:     Array of permitted current data request statuses or None (check skipped)

    :returns:            True if permitted, False if not
    :rtype:              Boolean
    """

    # Convert statuses to list of status enumeration elements
    if statuses is not None:
        def get_status(stat):
            return status[stat]
        statuses = map(get_status, statuses)

    return datarequest_action_permitted(ctx, request_id, roles, statuses)


def datarequest_action_permitted(ctx, request_id, roles, statuses):
    """Check if current user and data request status meet specified restrictions

    :param ctx:          Combined type of a callback and rei struct
    :param request_id:   Unique identifier of the data request
    :param roles:        Array of permitted roles (possible values: PM, ED, DM, DMC, OWN, REV)
    :param statuses:     Array of permitted current data request statuses or None (check skipped)

    :returns:            True if permitted, False if not
    :rtype:              Boolean
    """
    try:
        # Force conversion of request_id to string
        request_id = str(request_id)

        # Check status
        if ((statuses is not None) and (status_get(ctx, request_id) not in statuses)):
            return api.Error("permission_error", "Action not permitted: illegal status transition.")

        # Get current user roles
        current_user_roles = []
        if user.is_member_of(ctx, GROUP_PM):
            current_user_roles.append("PM")
        if user.is_member_of(ctx, GROUP_ED):
            current_user_roles.append("ED")
        if user.is_member_of(ctx, GROUP_DM):
            current_user_roles.append("DM")
        if user.is_member_of(ctx, GROUP_DMC):
            current_user_roles.append("DMC")
        if datarequest_is_owner(ctx, request_id):
            current_user_roles.append("OWN")
        if datarequest_is_reviewer(ctx, request_id):
            current_user_roles.append("REV")

        # Check user permissions (i.e. if at least 1 of the user's roles is on the permitted roles
        # list)
        if len(set(current_user_roles) & set(roles)) < 1:
            return api.Error("permission_error", "Action not permitted: insufficient user permissions.")

        # If both checks pass, user is permitted to perform action
        return True
    except error.UUError as e:
        return api.Error("internal_error", "Something went wrong during permission checking.")


@api.make()
def api_datarequest_roles_get(ctx, request_id=None):
    """Get roles of invoking user

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request (OWN and REV roles will not be checked
                       if this parameter is missing)

    :returns:          Array of user roles
    :rtype:            Array
    """
    roles = []
    if user.is_member_of(ctx, GROUP_PM):
        roles.append("PM")
    if user.is_member_of(ctx, GROUP_ED):
        roles.append("ED")
    if user.is_member_of(ctx, GROUP_DM):
        roles.append("DM")
    if user.is_member_of(ctx, GROUP_DMC):
        roles.append("DMC")
    if request_id is not None and datarequest_is_owner(ctx, request_id):
        roles.append("OWN")
    if request_id is not None and datarequest_is_reviewer(ctx, request_id):
        roles.append("REV")
    return roles


def datarequest_is_owner(ctx, request_id):
    """Check if the invoking user is also the owner of a given data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :return:           True if user_name is owner of specified data request else False
    :rtype:            bool
    """
    return datarequest_owner_get(ctx, request_id) == user.name(ctx)


def datarequest_owner_get(ctx, request_id):
    """Get the account name (i.e. email address) of the owner of a data request

    :param ctx:        Combined type of a callback and a rei struct
    :param request_id: Unique identifier of the data request
    :type  request_id: str

    :return:           Account name of data request owner
    :rtype:            string
    """
    # Construct path to the data request
    file_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, DATAREQUEST
                                      + JSON_EXT)

    # Get and return data request owner
    return jsonutil.read(ctx, file_path)['owner']


def datarequest_is_reviewer(ctx, request_id):
    """Check if a user is assigned as reviewer to a data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Boolean indicating if the user is assigned as reviewer
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Get username
    username = user.name(ctx)

    # Reviewers are stored in one or more assignedForReview attributes on
    # the data request, so our first step is to query the metadata of our
    # data request file for these attributes

    # Declare variables needed for retrieving the list of reviewers
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    reviewers = []

    # Retrieve list of reviewers
    rows = row_iterator(["META_DATA_ATTR_VALUE"],
                        "COLL_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = 'assignedForReview'".format(coll_path, DATAREQUEST + JSON_EXT),
                        AS_DICT, ctx)
    for row in rows:
        reviewers.append(row['META_DATA_ATTR_VALUE'])

    # Check if the reviewers list contains the current user
    is_reviewer = username in reviewers

    # Return the is_reviewer boolean
    return is_reviewer


@api.make()
def api_datarequest_schema_get(ctx, schema_name):
    return datarequest_schema_get(ctx, schema_name)


def datarequest_schema_get(ctx, schema_name):
    """Get schema and UI schema of a datarequest form

    :param ctx:         Combined type of a callback and rei struct
    :param schema_name: Name of schema

    :returns: Dict with schema and UI schema
    """
    # Define paths to schema and uischema
    coll_path = "/{}{}".format(user.zone(ctx), SCHEMACOLLECTION)
    schema_path = "{}/{}/{}".format(coll_path, schema_name, SCHEMA + JSON_EXT)
    uischema_path = "{}/{}/{}".format(coll_path, schema_name, UISCHEMA + JSON_EXT)

    # Retrieve and read schema and uischema
    try:
        schema = jsonutil.read(ctx, schema_path)
        uischema = jsonutil.read(ctx, uischema_path)
    except error.UUFileNotExistError:
        return api.Error("file_read_error", "Could not read schema because it doesn't exist.")

    # Return JSON with schema and uischema
    return {"schema": schema, "uischema": uischema}


def datarequest_provenance_write(ctx, request_id, request_status):
    """Write the timestamp of a status transition to a provenance log

    :param ctx:            Combined type of a callback and rei struct
    :param request_id:     Unique identifier of the data request
    :param request_status: Status of which to write a timestamp

    :returns:              Nothing
    """
    # Check if request ID is valid
    if re.search("^\d{10}$", request_id) is None:
        return api.Error("input_error", "Invalid request ID supplied: {}.".format(request_id))

    # Check if status parameter is valid
    if request_status not in status:
        return api.Error("input_error", "Invalid status parameter supplied: {}.".format(request_status.value))

    # Construct path to provenance log
    coll_path       = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    provenance_path = "{}/{}".format(coll_path, PROVENANCE + JSON_EXT)

    # Get timestamps
    timestamps = jsonutil.read(ctx, provenance_path)

    # Check if there isn't already a timestamp for the given status
    if request_status.value in timestamps:
        return api.Error("input_error", "Status ({}) has already been timestamped.".format(request_status.value))

    # Add timestamp
    current_time = str(datetime.now().strftime('%s'))
    timestamps[request_status.value] = current_time

    # Write timestamp to provenance log
    try:
        jsonutil.write(ctx, provenance_path, timestamps)
    except error.UUError as e:
        return api.Error("write_error", "Could not write timestamp to provenance log: {}.".format(e))


def datarequest_data_valid(ctx, data, schema_name):
    """Check if form data contains no errors

    :param ctx:         Combined type of a callback and rei struct
    :param data:        The form data to validate
    :param schema_name: Name of JSON schema against which to validate the form data

    :returns: Boolean indicating if datarequest is valid or API error
    """
    try:
        schema = datarequest_schema_get(ctx, schema_name)['schema']

        validator = jsonschema.Draft7Validator(schema)

        errors = list(validator.iter_errors(data))

        return len(errors) == 0
    except error.UUJsonValidationError as e:
        # File may be missing or not valid JSON
        return api.Error("validation_error",
                         "{} form data could not be validated against its schema.".format(schema_name))


def cc_email_addresses_get(contact_object):
    try:
        cc = contact_object['cc_email_addresses']
        return cc.replace(' ', '')
    except Exception:
        return None


###################################################
#          Datarequest workflow API calls         #
###################################################

@api.make()
def api_datarequest_browse(ctx, sort_on='name', sort_order='asc', offset=0, limit=10):
    """Get paginated datarequests, including size/modify date information.

    :param ctx:        Combined type of a callback and rei struct
    :param sort_on:    Column to sort on ('name', 'modified')
    :param sort_order: Column sort order ('asc' or 'desc')
    :param offset:     Offset to start browsing from
    :param limit:      Limit number of results

    :returns: Dict with paginated datarequests
    """
    coll = "/{}/{}".format(user.zone(ctx), DRCOLLECTION)

    def transform(row):
        # Remove ORDER_BY etc. wrappers from column names.
        x = {re.sub('.*\((.*)\)', '\\1', k): v for k, v in row.items()}

        return {'id':          x['COLL_NAME'].split('/')[-1],
                'name':        x['COLL_OWNER_NAME'],
                'create_time': int(x['COLL_CREATE_TIME']),
                'status':      x['META_DATA_ATTR_VALUE']}

    def transform_title(row):
        # Remove ORDER_BY etc. wrappers from column names.
        x = {re.sub('.*\((.*)\)', '\\1', k): v for k, v in row.items()}

        return {'id':          x['COLL_NAME'].split('/')[-1],
                'title':       x['META_DATA_ATTR_VALUE']}

    if sort_on == 'modified':
        # FIXME: Sorting on modify date is borked: There appears to be no
        # reliable way to filter out replicas this way - multiple entries for
        # the same file may be returned when replication takes place on a
        # minute boundary, for example.
        # We would want to take the max modify time *per* data name.
        # (or not? replication may take place a long time after a modification,
        #  resulting in a 'too new' date)
        ccols = ['COLL_NAME', 'ORDER(COLL_CREATE_TIME)', "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE"]
    else:
        ccols = ['ORDER(COLL_NAME)', 'COLL_CREATE_TIME', "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE"]

    if sort_order == 'desc':
        ccols = [x.replace('ORDER(', 'ORDER_DESC(') for x in ccols]

    qcoll = Query(ctx, ccols, "COLL_PARENT_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = 'status'".format(coll, DATAREQUEST + JSON_EXT),
                  offset=offset, limit=limit, output=query.AS_DICT)

    ccols_title = ['COLL_NAME', "META_DATA_ATTR_VALUE"]
    qcoll_title = Query(ctx, ccols_title, "COLL_PARENT_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = 'title'".format(coll, DATAREQUEST + JSON_EXT),
                        offset=offset, limit=limit, output=query.AS_DICT)

    colls = map(transform, list(qcoll))
    colls_title = map(transform_title, list(qcoll_title))

    # Merge datarequest title in results.
    for datarequest_title in colls_title:
        for datarequest in colls:
            if datarequest_title['id'] == datarequest['id']:
                datarequest['title'] = datarequest_title['title']
                break

    if len(colls) == 0:
        # No results at all?
        # Make sure the collection actually exists.
        if not collection.exists(ctx, coll):
            return api.Error('nonexistent', 'The given path does not exist')
        # (checking this beforehand would waste a query in the most common situation)

    return OrderedDict([('total', qcoll.total_rows()),
                        ('items', colls)])


def file_write_and_lock(ctx, coll_path, filename, data, readers):
    """Grant temporary write permission and write file to disk.

    :param ctx:       Combined type of a callback and rei struct
    :param coll_path: Path to collection of file
    :param filename:  Name of file
    :param data:      The data to be written to disk
    :param readers:   Array of user names that should be given read access to the file
    """

    file_path = "{}/{}".format(coll_path, filename)

    # Grant temporary write permission
    ctx.adminTempWritePermission(coll_path, "grant")

    # Write
    jsonutil.write(ctx, file_path, data)

    # Grant read permission to readers
    for reader in readers:
        msi.set_acl(ctx, "default", "read", reader, file_path)

    # Revoke temporary write permission
    msi.set_acl(ctx, "default", "null", user.full_name(ctx), file_path)
    ctx.adminTempWritePermission(coll_path, "revoke")


@api.make()
def api_datarequest_submit(ctx, data, draft, draft_request_id=None):
    """Persist a data request to disk.

    :param ctx:              Combined type of a callback and rei struct
    :param data:             Contents of the data request
    :param draft:            Boolean specifying whether the data request should be saved as draft
    :param draft_request_id: Unique identifier of the draft data request

    :returns: API status
    """
    # Set request owner in form data
    data['owner'] = user.name(ctx)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, DATAREQUEST):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(DATAREQUEST))

    # Permission check
    if (user.is_member_of(ctx, GROUP_PM) or user.is_member_of(ctx, GROUP_DM) or user.is_member_of(ctx, GROUP_ED)):
        return api.Error("permission_error", "Action not permitted.")

    # If we're not working with a draft, create a new request ID
    request_id = draft_request_id if draft_request_id else str(datetime.now().strftime('%s'))

    # Construct paths
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_path = "{}/{}".format(coll_path, DATAREQUEST + JSON_EXT)

    # If we're not working with a draft, initialize the data request collection
    if not draft_request_id:
        # Create collections
        try:
            dta_path         = "{}/{}".format(coll_path, DTA_PATHNAME)
            sigdta_path      = "{}/{}".format(coll_path, SIGDTA_PATHNAME)
            attachments_path = "{}/{}".format(coll_path, ATTACHMENTS_PATHNAME)

            collection.create(ctx, coll_path)
            collection.create(ctx, attachments_path)
            collection.create(ctx, dta_path)
            collection.create(ctx, sigdta_path)
        except error.UUError as e:
            return api.Error("create_collection_fail", "Could not create collection path: {}.".format(e))

        # Grant permissions on collections
        msi.set_acl(ctx, "default", "read", GROUP_DM, coll_path)
        msi.set_acl(ctx, "default", "read", GROUP_ED, coll_path)
        msi.set_acl(ctx, "default", "read", GROUP_DMC, coll_path)
        msi.set_acl(ctx, "default", "read", GROUP_PM, coll_path)
        msi.set_acl(ctx, "default", "own", "rods", coll_path)
        msi.set_acl(ctx, "default", "read", GROUP_DM, attachments_path)
        msi.set_acl(ctx, "default", "read", GROUP_ED, attachments_path)
        msi.set_acl(ctx, "default", "read", GROUP_DMC, attachments_path)
        msi.set_acl(ctx, "default", "read", GROUP_PM, attachments_path)
        msi.set_acl(ctx, "default", "own", "rods", attachments_path)
        msi.set_acl(ctx, "default", "read", user.full_name(ctx), attachments_path)
        msi.set_acl(ctx, "default", "read", GROUP_PM, dta_path)
        msi.set_acl(ctx, "default", "read", GROUP_DM, dta_path)
        msi.set_acl(ctx, "default", "read", user.full_name(ctx), dta_path)
        msi.set_acl(ctx, "default", "own", "rods", dta_path)
        msi.set_acl(ctx, "default", "read", GROUP_PM, sigdta_path)
        msi.set_acl(ctx, "default", "read", GROUP_DM, sigdta_path)
        msi.set_acl(ctx, "default", "read", user.full_name(ctx), sigdta_path)
        msi.set_acl(ctx, "default", "own", "rods", sigdta_path)

        # Create provenance log
        provenance_path = "{}/{}".format(coll_path, PROVENANCE + JSON_EXT)
        jsonutil.write(ctx, provenance_path, {})

        # Write data request
        jsonutil.write(ctx, file_path, data)

        # Apply initial permission restrictions to researcher
        msi.set_acl(ctx, "default", "null", user.full_name(ctx), provenance_path)
        msi.set_acl(ctx, "default", "read", user.full_name(ctx), coll_path)

    # Write form data to disk
    try:
        jsonutil.write(ctx, file_path, data)
    except error.UUError:
        return api.Error('write_error', 'Could not write datarequest to disk.')

    # Set the proposal fields as AVUs on the proposal JSON file
    avu_json.set_json_to_obj(ctx, file_path, "-d", "root", json.dumps(data))

    # If draft, set status
    if draft:
        status_set(ctx, request_id, status.DRAFT)
        # If new draft, return request ID of draft data request
        if not draft_request_id:
            return {"requestId": request_id}
        # If update of existing draft, return nothing
        else:
            return

    # Grant read permissions on data request
    msi.set_acl(ctx, "default", "read", GROUP_DM, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_ED, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_DMC, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_PM, file_path)

    # Revoke write permission
    msi.set_acl(ctx, "default", "read", user.full_name(ctx), file_path)

    # Update data request status
    if data['datarequest']['purpose'] == "Analyses for data assessment only (results will not be published)":
        status_set(ctx, request_id, status.DAO_SUBMITTED)
    else:
        if data['datarequest']['study_information']['attachments'] == "Yes":
            status_set(ctx, request_id, status.PENDING_ATTACHMENTS)
            return {"pendingAttachments": True, "requestId": request_id}
        else:
            status_set(ctx, request_id, status.SUBMITTED)
            return


@api.make()
def api_datarequest_get(ctx, request_id):
    """Retrieve a data request.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Dict with request JSON and status or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "DMC", "OWN"], None)

    # Get request status
    datarequest_status = status_get(ctx, request_id).value

    # Get request
    datarequest = datarequest_get(ctx, request_id)

    # Return JSON encoded results
    return {'requestJSON': datarequest, 'requestStatus': datarequest_status}


def datarequest_get(ctx, request_id):
    """Retrieve a data request.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datarequest JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename and filepath
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = DATAREQUEST + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the datarequest JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError as e:
        return api.Error("datarequest_read_fail", "Could not get contents of datarequest JSON file: {}.".format(e))


@api.make()
def api_datarequest_attachment_upload_permission(ctx, request_id, action):
    """
    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param action:     String specifying whether write permission must be granted ("grant") or
                       revoked ("grantread" or "revoke")

    :returns:          Nothing
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"], [status.PENDING_ATTACHMENTS])

    # Check if action is valid
    if action not in ["grant", "grantread"]:
        return api.Error("InputError", "Invalid action input parameter.")

    # Grant/revoke temporary write permissions
    attachments_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id,
                                             ATTACHMENTS_PATHNAME)
    ctx.adminTempWritePermission(attachments_path, action)
    return


@api.make()
def api_datarequest_attachment_post_upload_actions(ctx, request_id, filename):
    """Grant read permissions on the attachment to the owner of the associated data request.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param filename:   Filename of attachment
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"], [status.PENDING_ATTACHMENTS])

    # Set permissions
    file_path = coll_path = "/{}/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id,
                                                     ATTACHMENTS_PATHNAME, filename)
    msi.set_acl(ctx, "default", "read", GROUP_DM, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_PM, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_DMC, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_ED, file_path)


@api.make()
def api_datarequest_attachments_get(ctx, request_id):
    """Get all attachments of a given data request

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns:          List of attachment filenames
    """

    def get_filename(file_path):
        return file_path.split('/')[-1]

    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "DMC", "OWN"], None)

    # Return list of attachment filepaths
    coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id,
                                      ATTACHMENTS_PATHNAME)
    return map(get_filename, list(collection.data_objects(ctx, coll_path)))


@api.make()
def api_datarequest_attachments_submit(ctx, request_id):
    """Finalize the submission of uploaded attachments

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"], [status.PENDING_ATTACHMENTS])

    # Revoke ownership and write access
    coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, ATTACHMENTS_PATHNAME)
    for attachment_path in list(collection.data_objects(ctx, coll_path)):
        msi.set_acl(ctx, "default", "read", datarequest_owner_get(ctx, request_id), attachment_path)

    # Set status to dta_ready
    status_set(ctx, request_id, status.SUBMITTED)


@api.make()
def api_datarequest_preliminary_review_submit(ctx, data, request_id):
    """Persist a preliminary review to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the preliminary review
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, PR_REVIEW):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(PR_REVIEW))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM"], [status.SUBMITTED])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, PR_REVIEW + JSON_EXT, data, [GROUP_DM, GROUP_PM,
                                                                         GROUP_ED, GROUP_DMC])
    except error.UUError as e:
        return api.Error('write_error', 'Could not write preliminary review data to disk: {}'.format(e))

    # Get decision
    decision = data['preliminary_review']

    # Update data request status
    if decision == "Accepted for data manager review":
        status_set(ctx, request_id, status.PRELIMINARY_ACCEPT)
    elif decision == "Rejected":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.PRELIMINARY_REJECT)
    elif decision == "Rejected (resubmit)":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.PRELIMINARY_RESUBMIT)
    else:
        return api.Error("InvalidData", "Invalid value for preliminary_review in preliminary review JSON data.")


@api.make()
def api_datarequest_preliminary_review_get(ctx, request_id):
    """Retrieve a preliminary review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Preliminary review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "REV"], None)

    return datarequest_preliminary_review_get(ctx, request_id)


def datarequest_preliminary_review_get(ctx, request_id):
    """Retrieve a preliminary review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Preliminary review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = PR_REVIEW + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the review JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError as e:
        return api.Error("ReadError", "Could not get preliminary review data: {}.".format(e))


@api.make()
def api_datarequest_datamanager_review_submit(ctx, data, request_id):
    """Persist a datamanager review to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the datamanager review
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, DM_REVIEW):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(DM_REVIEW))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["DM"], [status.PRELIMINARY_ACCEPT])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, DM_REVIEW + JSON_EXT, data, [GROUP_DM, GROUP_PM,
                                                                         GROUP_ED, GROUP_DMC])
    except error.UUError:
        return api.Error('write_error', 'Could not write data manager review data to disk')

    # Get decision
    decision = data['datamanager_review']

    # Update data request status
    if decision == "Accepted":
        status_set(ctx, request_id, status.DATAMANAGER_ACCEPT)
    elif decision == "Rejected":
        status_set(ctx, request_id, status.DATAMANAGER_REJECT)
    elif decision == "Rejected (resubmit)":
        status_set(ctx, request_id, status.DATAMANAGER_RESUBMIT)
    else:
        return api.Error("InvalidData", "Invalid value for decision in data manager review JSON data.")


@api.make()
def api_datarequest_datamanager_review_get(ctx, request_id):
    """Retrieve a data manager review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datamanager review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "REV"], None)

    # Retrieve and return datamanager review
    return datarequest_datamanager_review_get(ctx, request_id)


def datarequest_datamanager_review_get(ctx, request_id):
    """Retrieve a data manager review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datamanager review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = DM_REVIEW + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the data manager review JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError as e:
        return api.Error("ReadError", "Could not get data manager review data: {}.".format(e))


@api.make()
def api_datarequest_dmr_review_submit(ctx, data, request_id):
    """Persist a datamanager review review to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the datamanager review review
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, DMR_REVIEW):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(DMR_REVIEW))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM"], [status.DATAMANAGER_ACCEPT,
                                                           status.DATAMANAGER_REJECT,
                                                           status.DATAMANAGER_RESUBMIT])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, DMR_REVIEW + JSON_EXT, data, [GROUP_DM, GROUP_PM,
                                                                          GROUP_ED, GROUP_DMC])
    except error.UUError:
        return api.Error('write_error', 'Could not write data manager review review data to disk.')

    # Get decision
    decision = data['decision']

    # Update data request status
    if decision == "Accepted for review":
        status_set(ctx, request_id, status.DATAMANAGER_REVIEW_ACCEPTED)
    elif decision == "Rejected":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.REJECTED_AFTER_DATAMANAGER_REVIEW)
    elif decision == "Rejected (resubmit)":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.RESUBMIT_AFTER_DATAMANAGER_REVIEW)
    else:
        return api.Error("InvalidData", "Invalid value for 'decision' key in datamanager review review JSON data.")


@api.make()
def api_datarequest_dmr_review_get(ctx, request_id):
    """Retrieve a data manager review review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datamanager review review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "REV"], None)

    # Retrieve and return datamanager review
    return datarequest_dmr_review_get(ctx, request_id)


def datarequest_dmr_review_get(ctx, request_id):
    """Retrieve datamanager review review

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datamanager review review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = DMR_REVIEW + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the data manager review review JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError as e:
        return api.Error("ReadError", "Could not get data manager review review data: {}.".format(e))


@api.make()
def api_datarequest_contribution_review_submit(ctx, data, request_id):
    """Persist a contribution review to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the contribution review
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, CONTRIB_REVIEW):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(CONTRIB_REVIEW))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["ED"], [status.DATAMANAGER_REVIEW_ACCEPTED])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, CONTRIB_REVIEW + JSON_EXT, data, [GROUP_DM, GROUP_PM,
                                                                              GROUP_ED, GROUP_DMC])
    except error.UUError:
        return api.Error('write_error', 'Could not write contribution review data to disk.')

    # Get decision
    decision = data['decision']

    # Update data request status
    if decision == "Accepted":
        status_set(ctx, request_id, status.CONTRIBUTION_ACCEPTED)
    elif decision == "Rejected":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.CONTRIBUTION_REJECTED)
    elif decision == "Rejected (resubmit)":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.CONTRIBUTION_RESUBMIT)
    else:
        return api.Error("InvalidData", "Invalid value for 'decision' key in contribution review JSON data.")


@api.make()
def api_datarequest_contribution_review_get(ctx, request_id):
    """Retrieve contribution review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Contribution review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "REV"], None)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = CONTRIB_REVIEW + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the contribution review JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError:
        return api.Error("ReadError", "Could not get contribution review data.")


@api.make()
def api_datarequest_assignment_submit(ctx, data, request_id):
    """Persist an assignment to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the assignment
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, ASSIGNMENT):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(ASSIGNMENT))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "ED", "DM", "REV"],
                                 [status.CONTRIBUTION_ACCEPTED])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, ASSIGNMENT + JSON_EXT, data, [GROUP_DM, GROUP_PM,
                                                                          GROUP_ED, GROUP_DMC])
    except error.UUError:
        return api.Error('write_error', 'Could not write assignment data to disk')

    # Update data request status
    assignees = json.dumps(data['assign_to'])
    assign_request(ctx, assignees, request_id)
    status_set(ctx, request_id, status.UNDER_REVIEW)


def assign_request(ctx, assignees, request_id):
    """Assign a data request to one or more DMC members for review.

    :param ctx:        Combined type of a callback and rei struct
    :param assignees:  JSON-formatted array of DMC members
    :param request_id: Unique identifier of the data request
    """
    # Construct data request collection path
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Assign the data request by adding a delayed rule that sets one or more
    # "assignedForReview" attributes on the datarequest (the number of
    # attributes is determined by the number of assignees) ...
    status = ""
    status_info = ""
    ctx.requestDatarequestMetadataChange(coll_path,
                                         "assignedForReview",
                                         assignees,
                                         str(len(json.loads(assignees))),
                                         status, status_info)

    # ... and triggering the processing of delayed rules
    ctx.adminDatarequestActions()


@api.make()
def api_datarequest_assignment_get(ctx, request_id):
    """Retrieve assignment.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datarequest assignment JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM"], None)

    return datarequest_assignment_get(ctx, request_id)


def datarequest_assignment_get(ctx, request_id):
    """Retrieve an assignment

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Assignment JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = ASSIGNMENT + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the assignment JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError:
        return api.Error("ReadError", "Could not get assignment data.")


@api.make()
def api_datarequest_review_submit(ctx, data, request_id):
    """Persist a data request review to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the review
    :param request_id: Unique identifier of the data request

    :returns: A JSON dict with status info for the front office
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, REVIEW):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(REVIEW))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM"], [status.UNDER_REVIEW])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, REVIEW + "_{}".format(user.name(ctx)) + JSON_EXT, data,
                            [GROUP_PM])
    except error.UUError as e:
        return api.Error('write_error', 'Could not write review data to disk: {}.'.format(e))

    # Remove the assignedForReview attribute of this user by first fetching
    # the list of reviewers ...
    reviewers = []

    iter = genquery.row_iterator(
        "META_DATA_ATTR_VALUE",
        "COLL_NAME = '{}' AND DATA_NAME = '{}' AND META_DATA_ATTR_NAME = 'assignedForReview'".format(coll_path, DATAREQUEST + JSON_EXT),
        genquery.AS_LIST, ctx)

    for row in iter:
        reviewer = row[0]
        reviewers.append(reviewer)

    # ... then removing the current reviewer from the list
    reviewers.remove(user.name(ctx))

    # ... and then updating the assignedForReview attributes
    status_code = ""
    status_info = ""
    ctx.requestDatarequestMetadataChange(coll_path,
                                         "assignedForReview",
                                         json.dumps(reviewers),
                                         str(len(reviewers)),
                                         status_code, status_info)
    ctx.adminDatarequestActions()

    # If there are no reviewers left, update data request status
    if len(reviewers) < 1:
        status_set(ctx, request_id, status.REVIEWED)


@api.make()
def api_datarequest_reviews_get(ctx, request_id):
    """Retrieve a data request review.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns: Datarequest review JSON or API error on failure
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "REV"], None)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = 'review_%.json'

    # Get the review JSON files
    reviews = []
    rows = row_iterator(["DATA_NAME"],
                        "COLL_NAME = '{}' AND DATA_NAME like '{}'".format(coll_path, file_name),
                        AS_DICT, ctx)
    for row in rows:
        file_path = "{}/{}".format(coll_path, row['DATA_NAME'])
        try:
            reviews.append(json.loads(data_object.read(ctx, file_path)))
        except error.UUError as e:
            return api.Error("ReadError", "Could not get review data: {}.".format(e))

    return json.dumps(reviews)


@api.make()
def api_datarequest_evaluation_submit(ctx, data, request_id):
    """Persist an evaluation to disk.

    :param ctx:        Combined type of a callback and rei struct
    :param data:       Contents of the evaluation
    :param request_id: Unique identifier of the data request

    :returns: API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Validate data against schema
    if not datarequest_data_valid(ctx, data, EVALUATION):
        return api.Error("validation_fail",
                         "{} form data did not pass validation against its schema.".format(EVALUATION))

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM"], [status.REVIEWED])

    # Construct path to collection
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, EVALUATION + JSON_EXT, data, [GROUP_PM])
    except error.UUError:
        return api.Error('write_error', 'Could not write evaluation data to disk')

    # Get decision
    decision = data['evaluation']

    # Update data request status
    if decision == "Approved":
        if status_get(ctx, request_id) == status.DAO_SUBMITTED:
            status_set(ctx, request_id, status.DAO_APPROVED)
        else:
            status_set(ctx, request_id, status.APPROVED)
    elif decision == "Rejected":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.REJECTED)
    elif decision == "Rejected (resubmit)":
        datarequest_feedback_write(ctx, request_id, data['feedback_for_researcher'])
        status_set(ctx, request_id, status.RESUBMIT)
    else:
        return api.Error("InvalidData", "Invalid value for 'evaluation' key in evaluation JSON data.")


def datarequest_evaluation_get(ctx, request_id):
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_name = EVALUATION + JSON_EXT
    file_path = "{}/{}".format(coll_path, file_name)

    # Get the contents of the assignment JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError:
        return api.Error("ReadError", "Could not get evaluation data.")


def datarequest_feedback_write(ctx, request_id, feedback):
    """ Write feedback to researcher to a separate file and grant the researcher read access

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param feedback:   String containing the feedback for the researcher

    :returns:          API status
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Construct path to feedback file
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)

    # Write form data to disk
    try:
        file_write_and_lock(ctx, coll_path, FEEDBACK + JSON_EXT, feedback, [GROUP_PM])
    except error.UUError:
        return api.Error('write_error', 'Could not write feedback data to disk.')

    # Grant researcher read permissions
    try:
        msi.set_acl(ctx, "default", "read", datarequest_owner_get(ctx, request_id),
                    "{}/{}".format(coll_path, FEEDBACK + JSON_EXT))
    except error.UUError:
        return api.Error("PermissionError", "Could not grant read permissions on the feedback file to the data request owner.")


@api.make()
def api_datarequest_feedback_get(ctx, request_id):
    """Get feedback for researcher

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns:          JSON-formatted string containing feedback for researcher
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"],
                                 [status.PRELIMINARY_REJECT, status.PRELIMINARY_RESUBMIT,
                                  status.REJECTED_AFTER_DATAMANAGER_REVIEW,
                                  status.RESUBMIT_AFTER_DATAMANAGER_REVIEW, status.REJECTED,
                                  status.RESUBMIT])

    # Construct filename
    coll_path = "/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id)
    file_path = "{}/{}".format(coll_path, FEEDBACK + JSON_EXT)

    # Get the contents of the feedback JSON file
    try:
        return data_object.read(ctx, file_path)
    except error.UUError as e:
        return api.Error("ReadError", "Could not get feedback data: {}.".format(e))


@api.make()
def api_datarequest_contribution_confirm(ctx, request_id):
    """Set the status of a submitted datarequest to CONTRIBUTION_CONFIRMED.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["ED"], [status.APPROVED])

    status_set(ctx, request_id, status.CONTRIBUTION_CONFIRMED)


@api.make()
def api_datarequest_dta_upload_permission(ctx, request_id, action):
    """
    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param action:     String specifying whether write permission must be granted ("grant") or
                       revoked ("revoke")

    :returns:          Nothing
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["DM"], [status.CONTRIBUTION_CONFIRMED,
                                                           status.DAO_APPROVED])

    # Check if action is valid
    if action not in ["grant", "revoke"]:
        return api.Error("InputError", "Invalid action input parameter.")

    # Grant/revoke temporary write permissions
    dta_coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, DTA_PATHNAME)
    ctx.adminTempWritePermission(dta_coll_path, action)


@api.make()
def api_datarequest_dta_post_upload_actions(ctx, request_id, filename):
    """Grant read permissions on the DTA to the owner of the associated data request.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param filename:   Filename of DTA
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["DM"], [status.CONTRIBUTION_CONFIRMED,
                                                           status.DAO_APPROVED])

    # Set permissions
    file_path = coll_path = "/{}/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, DTA_PATHNAME, filename)
    msi.set_acl(ctx, "default", "read", GROUP_DM, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_PM, file_path)
    msi.set_acl(ctx, "default", "read", datarequest_owner_get(ctx, request_id), file_path)

    # Set status to dta_ready
    status_set(ctx, request_id, status.DTA_READY)


@api.make()
def api_datarequest_dta_path_get(ctx, request_id):
    """Get path to DTA

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns:          Path to DTA
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "DM", "OWN"], None)

    coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, DTA_PATHNAME)
    return list(collection.data_objects(ctx, coll_path))[0]


@api.make()
def api_datarequest_signed_dta_upload_permission(ctx, request_id, action):
    """
    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param action:     String specifying whether write permission must be granted ("grant") or
                       revoked ("revoke")

    :returns:          Nothing
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"], [status.DTA_READY])

    # Check if action is valid
    if action not in ["grant", "revoke"]:
        return api.Error("InputError", "Invalid action input parameter.")

    # Grant/revoke temporary write permissions
    dta_coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, SIGDTA_PATHNAME)
    ctx.adminTempWritePermission(dta_coll_path, action)


@api.make()
def api_datarequest_signed_dta_post_upload_actions(ctx, request_id, filename):
    """Grant read permissions on the signed DTA to the datamanagers group.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    :param filename:   Filename of signed DTA
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["OWN"], [status.DTA_READY])

    # Set permissions
    file_path = coll_path = "/{}/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, SIGDTA_PATHNAME, filename)
    msi.set_acl(ctx, "default", "read", GROUP_DM, file_path)
    msi.set_acl(ctx, "default", "read", GROUP_PM, file_path)
    msi.set_acl(ctx, "default", "read", datarequest_owner_get(ctx, request_id), file_path)

    # Set status to dta_signed
    status_set(ctx, request_id, status.DTA_SIGNED)


@api.make()
def api_datarequest_signed_dta_path_get(ctx, request_id):
    """Get path to signed DTA

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request

    :returns:          Path to signed DTA
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["PM", "DM", "OWN"], None)

    coll_path = "/{}/{}/{}/{}".format(user.zone(ctx), DRCOLLECTION, request_id, SIGDTA_PATHNAME)
    return list(collection.data_objects(ctx, coll_path))[0]


@api.make()
def api_datarequest_data_ready(ctx, request_id):
    """Set the status of a submitted datarequest to DATA_READY.

    :param ctx:        Combined type of a callback and rei struct
    :param request_id: Unique identifier of the data request
    """
    # Force conversion of request_id to string
    request_id = str(request_id)

    # Permission check
    datarequest_action_permitted(ctx, request_id, ["DM"], [status.DTA_SIGNED])

    status_set(ctx, request_id, status.DATA_READY)


###################################################
#                   Email logic                   #
###################################################

def send_emails(ctx, obj_name, status_to):
    # Get request ID
    temp, _ = pathutil.chop(obj_name)
    _, request_id = pathutil.chop(temp)

    # Get datarequest status
    datarequest_status = status_get(ctx, request_id)

    # Determine and invoke the appropriate email routine
    if datarequest_status == status.DAO_SUBMITTED:
        datarequest_submit_emails(ctx, request_id, dao=True)

    elif datarequest_status == status.SUBMITTED:
        datarequest_submit_emails(ctx, request_id)

    elif datarequest_status in (status.PRELIMINARY_ACCEPT,
                                status.PRELIMINARY_REJECT,
                                status.PRELIMINARY_RESUBMIT):
        preliminary_review_emails(ctx, request_id, datarequest_status)

    elif datarequest_status in (status.DATAMANAGER_ACCEPT,
                                status.DATAMANAGER_REJECT,
                                status.DATAMANAGER_RESUBMIT):
        datamanager_review_emails(ctx, request_id, datarequest_status)

    elif datarequest_status in (status.DATAMANAGER_REVIEW_ACCEPTED,
                                status.REJECTED_AFTER_DATAMANAGER_REVIEW,
                                status.RESUBMIT_AFTER_DATAMANAGER_REVIEW):
        dmr_review_emails(ctx, request_id, datarequest_status)

    elif datarequest_status in (status.CONTRIBUTION_ACCEPTED,
                                status.CONTRIBUTION_REJECTED,
                                status.CONTRIBUTION_RESUBMIT):
        contribution_review_emails(ctx, request_id, datarequest_status)

    elif datarequest_status == status.UNDER_REVIEW:
        assignment_emails(ctx, request_id)

    elif datarequest_status == status.REVIEWED:
        review_emails(ctx, request_id)

    elif datarequest_status in (status.APPROVED,
                                status.REJECTED,
                                status.RESUBMIT):
        evaluation_emails(ctx, request_id, datarequest_status)

    elif datarequest_status == status.CONTRIBUTION_CONFIRMED:
        contribution_confirm_emails(ctx, request_id)

    elif datarequest_status == status.DAO_APPROVED:
        dao_approved_emails(ctx, request_id)

    elif datarequest_status == status.DTA_READY:
        dta_post_upload_actions_emails(ctx, request_id)

    elif datarequest_status == status.DTA_SIGNED:
        signed_dta_post_upload_actions_emails(ctx, request_id)

    elif datarequest_status == status.DATA_READY:
        data_ready_emails(ctx, request_id)


def datarequest_submit_emails(ctx, request_id, dao=False):
    # Get (source data for) email input parameters
    datarequest      = json.loads(datarequest_get(ctx, request_id))
    researcher       = datarequest['contact']
    researcher_email = datarequest_owner_get(ctx, request_id)
    cc               = cc_email_addresses_get(researcher)
    study_title      = datarequest['datarequest']['study_information']['title']
    pm_emails        = group.members(ctx, GROUP_PM)
    timestamp        = datetime.fromtimestamp(int(request_id)).strftime('%c')

    # Send email to researcher and project manager
    mail_datarequest_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                + researcher['family_name'], request_id, cc, dao)
    for pm_email in pm_emails:
        if dao:
            mail_datarequest_dao_pm(ctx, pm_email, request_id, researcher['given_name'] + ' '
                                    + researcher['family_name'], researcher_email,
                                    researcher['institution'], researcher['department'],
                                    timestamp, study_title)
        else:
            mail_datarequest_pm(ctx, pm_email, request_id, researcher['given_name'] + ' '
                                + researcher['family_name'], researcher_email,
                                researcher['institution'], researcher['department'], timestamp,
                                study_title)


def preliminary_review_emails(ctx, request_id, datarequest_status):
    # Get (source data for) email input parameters
    datamanager_emails = group.members(ctx, GROUP_DM)

    # Email datamanager
    if datarequest_status == status.PRELIMINARY_ACCEPT:
        for datamanager_email in datamanager_emails:
            mail_preliminary_review_accepted(ctx, datamanager_email, request_id)
        return

    # Email researcher with feedback and call to action
    elif datarequest_status in (status.PRELIMINARY_REJECT, status.PRELIMINARY_RESUBMIT):
        # Get additional (source data for) email input parameters
        datarequest             = json.loads(datarequest_get(ctx, request_id))
        researcher              = datarequest['contact']
        researcher_email        = datarequest_owner_get(ctx, request_id)
        cc                      = cc_email_addresses_get(researcher)
        pm_email                = group.members(ctx, GROUP_PM)[0]
        preliminary_review      = json.loads(datarequest_preliminary_review_get(ctx, request_id))
        feedback_for_researcher = preliminary_review['feedback_for_researcher']

        # Send emails
        if datarequest_status == status.PRELIMINARY_RESUBMIT:
            mail_resubmit(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)
        elif datarequest_status == status.PRELIMINARY_REJECT:
            mail_rejected(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)


def datamanager_review_emails(ctx, request_id, datarequest_status):
    # Get (source data for) email input parameters
    pm_emails           = group.members(ctx, GROUP_PM)
    datamanager_review  = json.loads(datarequest_datamanager_review_get(ctx, request_id))
    datamanager_remarks = (datamanager_review['datamanager_remarks'] if 'datamanager_remarks' in
                           datamanager_review else "")

    # Send emails
    for pm_email in pm_emails:
        if datarequest_status   == status.DATAMANAGER_ACCEPT:
            mail_datamanager_review_accepted(ctx, pm_email, request_id)
        elif datarequest_status == status.DATAMANAGER_RESUBMIT:
            mail_datamanager_review_resubmit(ctx, pm_email, datamanager_remarks,
                                             request_id)
        elif datarequest_status == status.DATAMANAGER_REJECT:
            mail_datamanager_review_rejected(ctx, pm_email, datamanager_remarks,
                                             request_id)


def dmr_review_emails(ctx, request_id, datarequest_status):
    # Get (source data for) email input parameters
    datarequest      = json.loads(datarequest_get(ctx, request_id))
    researcher       = datarequest['contact']
    researcher_email = datarequest_owner_get(ctx, request_id)
    cc               = cc_email_addresses_get(researcher)
    study_title      = datarequest['datarequest']['study_information']['title']
    dmr_review       = json.loads(datarequest_dmr_review_get(ctx, request_id))

    # Send emails
    if datarequest_status == status.DATAMANAGER_REVIEW_ACCEPTED:
        # Get additional email input parameters
        ed_emails = group.members(ctx, GROUP_ED)

        # Send emails
        mail_dmr_review_accepted_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                            + researcher['family_name'], request_id, cc)
        for ed_email in ed_emails:
            mail_dmr_review_accepted_executive_director(ctx, ed_email, study_title,
                                                        request_id)

    elif datarequest_status in (status.RESUBMIT_AFTER_DATAMANAGER_REVIEW,
                                status.REJECTED_AFTER_DATAMANAGER_REVIEW):
        # Get additional email input parameters
        feedback_for_researcher = dmr_review['feedback_for_researcher']
        pm_email                = group.members(ctx, GROUP_PM)[0]

        # Send emails
        if datarequest_status == status.RESUBMIT_AFTER_DATAMANAGER_REVIEW:
            mail_resubmit(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)
        elif datarequest_status == status.REJECTED_AFTER_DATAMANAGER_REVIEW:
            mail_rejected(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)


def contribution_review_emails(ctx, request_id, datarequest_status):
    # Get parameters
    pm_emails = group.members(ctx, GROUP_PM)
    pm_email = pm_emails[0]

    # Send emails
    if datarequest_status == status.CONTRIBUTION_ACCEPTED:
        for pm_email in pm_emails:
            mail_contribution_review_accepted(ctx, pm_email, request_id)
    elif datarequest_status in (status.CONTRIBUTION_REJECTED,
                                status.CONTRIBUTION_RESUBMIT):
        # Get additional parameters
        researcher       = datarequest['contact']
        researcher_email = datarequest_owner_get(ctx, request_id)
        cc               = cc_email_addresses_get(researcher)

        if datarequest_status == status.CONTRIBUTION_REJECTED:
            mail_resubmit(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)
        elif datarequest_status == status.CONTRIBUTION_RESUBMIT:
            mail_rejected(ctx, researcher_email, researcher['given_name'] + ' '
                          + researcher['family_name'], feedback_for_researcher, pm_email,
                          request_id, cc)


def assignment_emails(ctx, request_id):
    # Get (source data for) email input parameters
    datarequest      = json.loads(datarequest_get(ctx, request_id))
    researcher       = datarequest['contact']
    researcher_email = datarequest_owner_get(ctx, request_id)
    cc               = cc_email_addresses_get(researcher)
    study_title      = datarequest['datarequest']['study_information']['title']
    assignment       = json.loads(datarequest_assignment_get(ctx, request_id))
    assignees        = assignment['assign_to']

    # Send emails
    mail_assignment_accepted_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                        + researcher['family_name'], request_id, cc)
    for assignee_email in assignees:
        mail_assignment_accepted_assignee(ctx, assignee_email, study_title,
                                          request_id)


def review_emails(ctx, request_id):
    # Get (source data for) email input parameters
    datarequest       = json.loads(datarequest_get(ctx, request_id))
    researcher        = datarequest['contact']
    researcher_email  = datarequest_owner_get(ctx, request_id)
    cc                = cc_email_addresses_get(researcher)
    pm_emails         = group.members(ctx, GROUP_PM)

    # Send emails
    mail_review_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                           + researcher['family_name'], request_id, cc)
    for pm_email in pm_emails:
        mail_review_pm(ctx, pm_email, request_id)


def evaluation_emails(ctx, request_id, datarequest_status):
    # Get (source data for) email input parameters
    datarequest             = json.loads(datarequest_get(ctx, request_id))
    researcher              = datarequest['contact']
    researcher_email        = datarequest_owner_get(ctx, request_id)
    cc                      = cc_email_addresses_get(researcher)
    evaluation              = json.loads(datarequest_evaluation_get(ctx, request_id))
    feedback_for_researcher = (evaluation['feedback_for_researcher'] if 'feedback_for_researcher' in
                               evaluation else "")
    pm_email                = group.members(ctx, GROUP_PM)[0]
    ed_emails               = group.members(ctx, GROUP_ED)

    # Send emails
    if datarequest_status == status.APPROVED:
        mail_evaluation_approved_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                            + researcher['family_name'], request_id, cc)
        for ed_email in ed_emails:
            mail_evaluation_approved_ed(ctx, ed_email, request_id)
    elif datarequest_status == status.RESUBMIT:
        mail_resubmit(ctx, researcher_email, researcher['given_name'] + ' '
                      + researcher['family_name'], feedback_for_researcher, pm_email, request_id,
                      cc)
    elif datarequest_status == status.REJECTED:
        mail_rejected(ctx, researcher_email, researcher['given_name'] + ' '
                      + researcher['family_name'], feedback_for_researcher, pm_email, request_id,
                      cc)


def contribution_confirm_emails(ctx, request_id):
    # Get parameters
    datarequest        = json.loads(datarequest_get(ctx, request_id))
    researcher         = datarequest['contact']
    researcher_email   = datarequest_owner_get(ctx, request_id)
    cc                 = cc_email_addresses_get(researcher)
    datamanager_emails = group.members(ctx, GROUP_DM)

    # Send emails
    mail_contribution_confirm_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                         + researcher['family_name'], request_id, cc)
    for datamanager_email in datamanager_emails:
        mail_contribution_confirm_dm(ctx, datamanager_email, request_id)


def dao_approved_emails(ctx, request_id):
    # Get parameters
    datarequest        = json.loads(datarequest_get(ctx, request_id))
    researcher         = datarequest['contact']
    researcher_email   = datarequest_owner_get(ctx, request_id)
    cc                 = cc_email_addresses_get(researcher)
    datamanager_emails = group.members(ctx, GROUP_DM)

    # Send emails
    mail_dao_approved_researcher(ctx, researcher_email, researcher['given_name'] + ' '
                                 + researcher['family_name'], request_id, cc)
    for datamanager_email in datamanager_emails:
        mail_contribution_confirm_dm(ctx, datamanager_email, request_id)


def dta_post_upload_actions_emails(ctx, request_id):
    # Get (source data for) email input parameters
    datarequest      = json.loads(datarequest_get(ctx, request_id))
    researcher       = datarequest['contact']
    researcher_email = datarequest_owner_get(ctx, request_id)
    cc               = cc_email_addresses_get(researcher)

    # Send email
    mail_dta(ctx, researcher_email, researcher['given_name'] + ' ' + researcher['family_name'],
             request_id, cc)


def signed_dta_post_upload_actions_emails(ctx, request_id):
    # Get (source data for) email input parameters
    datamanager_emails = group.members(ctx, GROUP_DM)

    # Send email
    for datamanager_email in datamanager_emails:
        mail_signed_dta(ctx, datamanager_email, request_id)


def data_ready_emails(ctx, request_id):
    # Get (source data for) email input parameters
    datarequest       = json.loads(datarequest_get(ctx, request_id))
    researcher        = datarequest['contact']
    researcher_email  = datarequest_owner_get(ctx, request_id)
    cc                = cc_email_addresses_get(researcher)
    datamanager_email = group.members(ctx, GROUP_DM)[0]

    # Send email
    mail_data_ready(ctx, researcher_email, researcher['given_name'] + ' '
                    + researcher['family_name'], datamanager_email, request_id, cc)


###################################################
#                 Email templates                 #
###################################################

def mail_datarequest_researcher(ctx, researcher_email, researcher_name, request_id, cc, dao):
    subject = "YOUth data request {} (data assessment only): submitted".format(request_id) if dao else "YOUth data request {}: submitted".format(request_id)

    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject=subject,
                     body="""Dear {},

Your data request has been submitted.

You will be notified by email of the status of your request. You may also log into Yoda to view the status and other information about your data request.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_datarequest_pm(ctx, pm_email, request_id, researcher_name, researcher_email,
                        researcher_institution, researcher_department, submission_date,
                        proposal_title):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: submitted".format(request_id),
                     body="""Dear project manager,

A new data request has been submitted.

Submitted by: {} ({})
Affiliation: {}, {}
Date: {}
Request ID: {}
Proposal title: {}

The following link will take you to the preliminary review form: https://{}/datarequest/preliminary_review/{}.

With kind regards,
YOUth
""".format(researcher_name, researcher_email, researcher_institution, researcher_department,
                         submission_date, request_id, proposal_title, YODA_PORTAL_FQDN, request_id))


def mail_datarequest_dao_pm(ctx, pm_email, request_id, researcher_name, researcher_email,
                            researcher_institution, researcher_department, submission_date,
                            proposal_title):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {} (data assessment only): submitted".format(request_id),
                     body="""Dear project manager,

A new data request (for the purpose of data assessment only) has been submitted.

Submitted by: {} ({})
Affiliation: {}, {}
Date: {}
Request ID: {}
Proposal title: {}

The following link will take you to the evaluation form: https://{}/datarequest/evaluate/{}.

With kind regards,
YOUth
""".format(researcher_name, researcher_email, researcher_institution, researcher_department,
                         submission_date, request_id, proposal_title, YODA_PORTAL_FQDN, request_id))


def mail_preliminary_review_accepted(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to=datamanager_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: accepted for data manager review".format(request_id),
                     body="""Dear data manager,

Data request {} has been approved for review by the YOUth project manager.

You are now asked to review the data request for any potential problems concerning the requested data and to submit your recommendation (accept, resubmit, or reject) to the YOUth project manager.

The following link will take you directly to the review form: https://{}/datarequest/datamanager_review/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_datamanager_review_accepted(ctx, pm_email, request_id):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: accepted by data manager".format(request_id),
                     body="""Dear project manager,

Data request {} has been accepted by the data manager.

The data manager's review is advisory. Please review the data manager's review. To do so, please navigate to the data manager review review form using this link https://{}/datarequest/dmr_review/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_datamanager_review_resubmit(ctx, pm_email, datamanager_remarks, request_id):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: rejected (resubmit) by data manager".format(request_id),
                     body="""Dear project manager,

Data request {} has been rejected (resubmission allowed) by the data manager for the following reason(s):

{}

The data manager's review is advisory. Please consider the objections raised and then review the data manager's review. To do so, please navigate to the data manager review review form using this link https://{}/datarequest/dmr_review/{}.

With kind regards,
YOUth
""".format(request_id, datamanager_remarks, YODA_PORTAL_FQDN, request_id))


def mail_datamanager_review_rejected(ctx, pm_email, datamanager_remarks, request_id):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: rejected by data manager".format(request_id),
                     body="""Dear project manager,

Data request {} has been rejected by the data manager for the following reason(s):

{}

The data manager's review is advisory. Please consider the objections raised and then review the data manager's review. To do so, please navigate to the data manager review review form using this link https://{}/datarequest/dmr_review/{}.

With kind regards,
YOUth
""".format(request_id, datamanager_remarks, YODA_PORTAL_FQDN, request_id))


def mail_dmr_review_accepted_researcher(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: under review".format(request_id),
                     body="""Dear {},

Your data request has passed a preliminary assessment and is now under review.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_dmr_review_accepted_executive_director(ctx, ed_email, proposal_title, request_id):
    return mail.send(ctx,
                     to=ed_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: accepted for review".format(request_id),
                     body="""Dear executive director,

Data request {} (proposal title: \"{}\") has been accepted for review. You are now asked to review the proposed contribution. To do so, please navigate to the contribution review form using this link: https://{}/datarequest/contribution_review/{}.

With kind regards,
YOUth
""".format(request_id, proposal_title, YODA_PORTAL_FQDN, request_id))


def mail_contribution_review_accepted(ctx, pm_email, request_id):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: contribution accepted".format(request_id),
                     body="""Dear project manager,

The contribution proposed in data request {} has been accepted by the executive director. You are now asked to assign the data request for review by the Data Management Committee. To do so, please navigate to the assignment form using this link: https://{}/datarequest/assign/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_assignment_accepted_researcher(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: assigned".format(request_id),
                     body="""Dear {},

Your data request has been assigned for review.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_assignment_accepted_assignee(ctx, assignee_email, proposal_title, request_id):
    return mail.send(ctx,
                     to=assignee_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: assigned".format(request_id),
                     body="""Dear DMC member,

Data request {} (proposal title: \"{}\") has been assigned to you for review. Please sign in to Yoda to view the data request and submit your review.

The following link will take you directly to the review form: https://{}/datarequest/review/{}.

With kind regards,
YOUth
""".format(request_id, proposal_title, YODA_PORTAL_FQDN, request_id))


def mail_review_researcher(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: reviewed".format(request_id),
                     body="""Dear {},

Your data request been reviewed by the YOUth Data Management Committee and is awaiting final evaluation by the YOUth project manager.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_review_pm(ctx, pm_email, request_id):
    return mail.send(ctx,
                     to=pm_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: reviewed".format(request_id),
                     body="""Dear project manager,

Data request {} has been reviewed by the YOUth Data Management Committee and is awaiting your final evaluation.

Please log into Yoda to evaluate the data request. The following link will take you directly to the evaluation form: https://{}/datarequest/evaluate/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_evaluation_approved_researcher(ctx, researcher_email, researcher_name,
                                        request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: approved".format(request_id),
                     body="""Dear {},

Congratulations! Your data request has been approved. The YOUth executive director will now confirm the reception or finalization of your contribution. If any further information or action is required of you, you will be contacted by the executive director.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_evaluation_approved_ed(ctx, ed_email, request_id):
    return mail.send(ctx,
                     to=ed_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: approved".format(request_id),
                     body="""Dear executive director,

Data request {} has been approved by the YOUth project manager. You are now asked to confirm the reception or finalization of the agreed upon contribution. After having done so, please navigate to the data request and click the "Confirm contribution" button.

The following link will take you directly to the data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_contribution_confirm_researcher(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: contribution confirmed".format(request_id),
                     body="""Dear {},

Your contribution has been confirmed. The YOUth data manager will now create a Data Transfer Agreement for you to sign. You will be notified when it is ready.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_contribution_confirm_dm(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to=datamanager_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: approved".format(request_id),
                     body="""Dear data manager,

Data request {} has been approved by the YOUth project manager. Please sign in to Yoda to upload a Data Transfer Agreement for the researcher.

The following link will take you directly to the data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_dao_approved_researcher(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {} (data assessment only): approved".format(request_id),
                     body="""Dear {},

Your data request has been approved. The YOUth data manager will now create a Data Transfer Agreement for you to sign. You will be notified when it is ready.

The following link will take you directly to the data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_resubmit(ctx, researcher_email, researcher_name, feedback_for_researcher, pm_email,
                  request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: rejected (resubmit)".format(request_id),
                     body="""Dear {},

Your data request has been rejected for the following reason(s):

{}

You are however allowed to resubmit your data request. You may do so using this link: https://{}/datarequest/add/{}.

If you wish to object against this rejection, please contact the YOUth project manager ({}).

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, YODA_PORTAL_FQDN, request_id, pm_email,
                         YODA_PORTAL_FQDN, request_id))


def mail_rejected(ctx, researcher_email, researcher_name, feedback_for_researcher, pm_email,
                  request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: rejected".format(request_id),
                     body="""Dear {},

Your data request has been rejected for the following reason(s):

{}

If you wish to object against this rejection, please contact the YOUth project manager ({}).

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

With kind regards,
YOUth
""".format(researcher_name, feedback_for_researcher, pm_email, YODA_PORTAL_FQDN, request_id))


def mail_dta(ctx, researcher_email, researcher_name, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: DTA ready".format(request_id),
                     body="""Dear {},

The YOUth data manager has created a Data Transfer Agreement to formalize the transfer of the data you have requested. Please sign in to Yoda to download and read the Data Transfer Agreement.

The following link will take you directly to your data request: https://{}/datarequest/view/{}.

If you do not object to the agreement, please upload a signed copy of the agreement. After this, the YOUth data manager will prepare the requested data and will provide you with instructions on how to download them.

With kind regards,
YOUth
""".format(researcher_name, YODA_PORTAL_FQDN, request_id))


def mail_signed_dta(ctx, datamanager_email, request_id):
    return mail.send(ctx,
                     to=datamanager_email,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: DTA signed".format(request_id),
                     body="""Dear data manager,

The researcher has uploaded a signed copy of the Data Transfer Agreement for data request {}.

Please log in to Yoda to review this copy. The following link will take you directly to the data request: https://{}/datarequest/view/{}.

After verifying that the document has been signed correctly, you may prepare the data for download. When the data is ready for the researcher to download, please click the \"Data ready\" button. This will notify the researcher by email that the requested data is ready. The email will include instructions on downloading the data.

With kind regards,
YOUth
""".format(request_id, YODA_PORTAL_FQDN, request_id))


def mail_data_ready(ctx, researcher_email, researcher_name, datamanager_email, request_id, cc):
    return mail.send(ctx,
                     to=researcher_email,
                     cc=cc,
                     actor=user.full_name(ctx),
                     subject="YOUth data request {}: data ready".format(request_id),
                     body="""Dear {},

The data you have requested is ready for you to download! For information on how to access the data through Yoda, see https://www.uu.nl/en/research/yoda/guide-to-yoda/i-want-to-start-using-yoda or contact the YOUth data manager ({}).

With kind regards,
YOUth
""".format(researcher_name, datamanager_email))
