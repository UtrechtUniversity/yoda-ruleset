"""Functions for communicating with SRAM and some utilities."""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import datetime
import time
from typing import Dict, List, Optional, Union

import genquery
import requests

from util import *

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204


def _request_headers() -> Dict[str, str]:
    """Return SRAM API request headers with bearer token."""
    return {
        'Content-Type': 'application/json',
        'charset': 'UTF-8',
        'Authorization': f'bearer {config.sram_api_key}'
    }


def post_collaboration(ctx: rule.Context, group_name: str, description: str) -> Dict:
    """Create SRAM Collaborative Organisation Identifier.

    :param ctx:             Combined type of a callback and rei struct
    :param group_name:      Name of the group to create
    :param description:     Description of the group to create

    :returns: JSON object with new collaboration details
    """
    url = f"{config.sram_rest_api_url}/api/collaborations/v1"

    group_type = ''
    if group_name.split('-')[0] in ('research', 'datamanager', 'priv', 'deposit'):
        group_type = group_name.split('-')[0]

    # Add current user as CO admin if username is a valid email.
    # Fallback to CO default admins if username is not a valid email.
    admin_user = user.name(ctx)
    administrators = [admin_user] if yoda_names.is_email_username(admin_user) else config.sram_co_default_admins

    # Build SRAM payload.
    payload = {
        "name": 'yoda-' + group_name,
        "description": description,
        "disable_join_requests": True,
        "disclose_member_information": True,
        "disclose_email_information": True,
        "administrators": administrators,
        "logo": config.sram_co_logo,
        "tags": [config.sram_co_default_label, group_type]
    }

    if config.sram_verbose_logging:
        log.write(ctx, f"post_collaboration post {url}: {payload}")

    response = requests.post(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)
    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, f"post_collaboration response: {data}")

    return data


def delete_collaboration(ctx: rule.Context, co_identifier: str) -> bool:
    """Delete SRAM Collaborative Organisation.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier

    :returns: Boolean indicating of deletion of collaboration succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"delete_collaboration error: CO identifier is invalid {co_identifier}")
        return False

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration post {url}")

    response = requests.delete(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration response: {response.status_code}")

    return response.status_code == HTTP_NO_CONTENT


def delete_collaboration_membership(ctx: rule.Context, co_identifier: str, uuid: str) -> bool:
    """Delete SRAM Collaborative Organisation membership.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param uuid:          Unique id of the user

    :returns: Boolean indicating of deletion of collaboration membership succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"delete_collaboration_membership error: CO identifier is invalid {co_identifier}")
        return False

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}/members/{uuid}"

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration_membership post {url}")

    response = requests.delete(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration_membership response: {response.status_code}")

    return response.status_code == HTTP_NO_CONTENT


def put_collaboration_invitation(ctx: rule.Context, group_name: str, username: str, co_identifier: str) -> bool:
    """Create SRAM Collaborative Organisation Identifier.

    :param ctx:           Combined type of a ctx and rei struct
    :param group_name:    Name of the group the user is to invited to join
    :param username:      Name of the user to be invited
    :param co_identifier: SRAM identifier of the group the user is to invited to join

    :returns: Boolean indicating if put of new collaboration invitation succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"put_collaboration_invitation error: CO identifier is invalid {co_identifier}")
        return False

    # Request SRAM to lookup possible existing invitation for this user.
    invitations = get_open_invitations(ctx, co_identifier)

    if config.sram_verbose_logging:
        if invitations:
            log.write(ctx, f"put_collaboration_invitation response: {invitations.status_code}")

    if invitations:
        for invite in invitations.json():
            if invite['invitation']['email'] == username and invite['status'] == 'open':
                if config.sram_verbose_logging:
                    log.write(ctx, f"put_collaboration_invitation error: invitation for {username} already exists")
                return True

    # Now plus a year.
    expiration_date = datetime.datetime.fromtimestamp(int(time.time() + 3600 * 24 * 365)).strftime('%Y-%m-%d')

    # Get epoch expiry date.
    date = datetime.datetime.strptime(expiration_date, "%Y-%m-%d")
    epoch = datetime.datetime.utcfromtimestamp(0)
    epoch_date = int((date - epoch).total_seconds()) * 1000

    # Build SRAM payload.
    payload = {
        "collaboration_identifier": co_identifier,
        "message": f"Invitation to join Yoda group {group_name}",
        "intended_role": "member",
        "invitation_expiry_date": epoch_date,
        "invites": [username],
        "groups": []
    }
    url = f"{config.sram_rest_api_url}/api/invitations/v1/collaboration_invites"
    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation put {url}: {payload}")

    response = requests.put(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation response: {response.status_code}")

    return response.status_code == HTTP_CREATED


def connect_service_collaboration(ctx: rule.Context, co_identifier: str) -> bool:
    """Connect a service to an existing SRAM collaboration.

    :param ctx:           Combined type of a ctx and rei struct
    :param co_identifier: SRAM identifier of the Co to connect the service to

    :returns: Boolean indicating if connecting a service to an existing collaboration succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"connect_service_collaboration error: CO identifier is invalid {co_identifier}")
        return False

    url = f"{config.sram_rest_api_url}/api/collaborations_services/v1/connect_collaboration_service/{co_identifier}"

    # Build SRAM payload.
    payload = {
        "service_entity_id": config.sram_service_entity_id
    }

    if config.sram_verbose_logging:
        log.write(ctx, f"connect_service_collaboration put {url}: {payload}")

    response = requests.put(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"connect_service_collaboration response: {response.status_code}")

    return response.status_code == HTTP_CREATED


def update_collaboration_membership(ctx: rule.Context, co_identifier: str, uuid: str, new_role: str) -> bool:
    """Update SRAM Collaborative Organisation membership.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param uuid:          Unique id of the user
    :param new_role:      New role of the user

    :returns: Boolean indicating that updation of collaboration membership succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"update_collaboration_membership error: CO identifier is invalid {co_identifier}")
        return False

    if not misc.is_valid_uuid(uuid):
        log.write(ctx, f"update_collaboration_membership error: User uuid is invalid {uuid}")
        return False

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}/members"
    payload = {
        "role": 'admin' if new_role == 'manager' else 'member',
        "uid": uuid
    }

    if config.sram_verbose_logging:
        log.write(ctx, f"update_collaboration_membership put {url}")

    response = requests.put(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"update_collaboration_membership response: {response.status_code}")

    return response.status_code == HTTP_CREATED


def get_co_members(ctx: rule.Context, co_identifier: str) -> List[Dict[str, str]]:
    """Get SRAM collaboration members with their uids.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier

    :returns: List of dicts containing email and uid of SRAM collaboration members
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"get_co_members error: CO identifier is invalid {co_identifier}")
        return []

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"get_co_members get {url}")

    response = requests.get(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)
    if response.status_code != HTTP_OK:
        if config.sram_verbose_logging:
            log.write(ctx, f"get_co_members response: {response.status_code}")
        return []

    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, f"get_co_members response: {data}")

    return [
        {
            'email': member['user']['email'],
            'uid': member['user']['uid']
        }
        for member in data.get('collaboration_memberships', [])
    ]


def get_co_member_uid(ctx: rule.Context, co_identifier: str, user_name: str) -> str:
    """Get SRAM collaboration member uid.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param user_name:     Name of the user

    :returns: Unique id of the user
    """
    co_members = get_co_members(ctx, co_identifier)

    for member in co_members:
        if user_name.lower() == member['email'].lower():
            if config.sram_verbose_logging:
                log.write(ctx, f"get_uid user_name: {user_name}, uuid: {member['uid']}")
            return member['uid']

    if config.sram_verbose_logging:
        log.write(ctx, f"get_uid user_name: {user_name}, uuid: not found")

    return ''


def is_user_co_member(ctx: rule.Context, co_identifier: str, user_name: str) -> bool:
    """Check if a user is a member of a SRAM collaboration.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param user_name:     Name of the user (email)

    :returns: Boolean indicating if the user is a member of the collaboration
    """
    co_members = get_co_members(ctx, co_identifier)

    is_member = any(user_name.lower() == member['email'].lower() for member in co_members)

    if config.sram_verbose_logging:
        log.write(ctx, f"is_user_co_member user_name: {user_name}, is_member: {is_member}")

    return is_member


def get_co_identifier(ctx: rule.Context, group_name: str) -> Optional[str]:
    """Retrieve the SRAM CO identifier of a Yoda group if the group is a SRAM CO.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group

    :returns: Return SRAM CO identifier if the Yoda group is a SRAM CO else None
    """
    if not config.enable_sram:
        return None

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        f"USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'co_identifier' AND USER_GROUP_NAME = '{group_name}'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if row[0] and misc.is_valid_uuid(row[0]):
            return row[0]

    return None


def is_user_marked_invited(ctx: rule.Context, username: str, group_name: str) -> bool:
    """Check in user metadata if user is marked as invited to SRAM CO.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group user is invited to

    :returns: Boolean indicating where the user is marked as invited to SRAM CO
    """
    attr_name = f"{constants.UUORGMETADATAPREFIX}sram_invited"
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        f"USER_GROUP_NAME = '{username}' AND META_USER_ATTR_NAME = '{attr_name}'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if row[0] == group_name:
            return True

    return False


def get_open_invitations(ctx: rule.Context, co_identifier: str) -> Union[bool, requests.Response]:
    """Get open invitations for a SRAM CO.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier

    :returns: Response including status code
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"put_collaboration_invitation error: CO identifier is invalid {co_identifier}")
        return False

    # Request SRAM to lookup possible existing invitation for this user.
    url = f"{config.sram_rest_api_url}/api/invitations/v1/invitations/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"get_open_invitations get: {url}")

    response = requests.get(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"get_open_invitations response: {response.status_code}")

    if response.status_code != HTTP_OK:
        log.write(ctx, f"get_open_invitations error: unable to retrieve existing invitations - http {response.status_code}")
        return False

    return response


def delete_pending_invitation(ctx: rule.Context, co_identifier: str, username: str) -> bool:
    """Delete pending invitation for a user in SRAM Collaborative Organisation.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param username:      Name of the user whose invitation needs to be deleted

    :returns: Boolean indicating of deletion of invitation succeeded
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"delete_collaboration error: CO identifier is invalid {co_identifier}")
        return False

    invitation_uuid = ''

    # Get unique id of open invitation for a user
    invitations = get_open_invitations(ctx, co_identifier)

    if invitations:
        for invite in invitations.json():
            if invite['invitation']['email'] == username and invite['status'] == 'open':
                invitation_uuid = invite['invitation']['identifier']

    if not misc.is_valid_uuid(invitation_uuid):
        log.write(ctx, f"No open invitations exist for user: {username}")
        return True

    url = f"{config.sram_rest_api_url}/api/invitations/v1/{invitation_uuid}"

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_pending_invitation delete {url}")

    response = requests.delete(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_pending_invitation response: {response.status_code}")

    return response.status_code == HTTP_NO_CONTENT
