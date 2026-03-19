"""Functions for communicating with SRAM and some utilities."""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import datetime
import time
from typing import Dict, List, Optional

import genquery
import requests

from util import *


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

    disable_join_requests = True

    # Add current user as CO admin if username is a valid email.
    # Fallback to CO default admins if username is not a valid email.
    admin_user = user.name(ctx)
    administrators = [admin_user] if yoda_names.is_email_username(admin_user) else config.sram_co_default_admins

    # Build SRAM payload.
    payload = {
        "name": 'yoda-' + group_name,
        "description": description,
        "disable_join_requests": disable_join_requests,
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


def get_uid(ctx: rule.Context, co_identifier: str, user_name: str) -> str:
    """Get SRAM Collaboration member uid.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param user_name:     Name of the user

    :returns: Unique id of the user
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"get_uid error: CO identifier is invalid {co_identifier}")
        return ''

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"get_uid get {url}")

    response = requests.get(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)
    if response.status_code != 200:
        if config.sram_verbose_logging:
            log.write(ctx, f"get_uid response: {response.status_code}")
        return ''

    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, f"get_uid response: {data}")

    uid = ''
    for key in data['collaboration_memberships']:
        sram_name = key['user']['email']
        if user_name.lower() == sram_name.lower():
            uid = key['user']['uid']

    if config.sram_verbose_logging:
        log.write(ctx, f"get_uid user_name: {user_name}, uuid: {uid}")

    return uid


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

    return response.status_code == 204


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

    if not misc.is_valid_uuid(uuid):
        log.write(ctx, f"delete_collaboration_membership error: User uuid is invalid {uuid}")
        return False

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}/members/{uuid}"

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration_membership post {url}")

    response = requests.delete(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"delete_collaboration_membership response: {response.status_code}")

    return response.status_code == 204


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

    # Request SRAM to lookup poosible existing invitation for this user.
    url = f"{config.sram_rest_api_url}/api/invitations/v1/invitations/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation get: {url}")

    response = requests.get(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation response: {response.status_code}")

    if response.status_code != 200:
        log.write(ctx, f"put_collaboration_invitation error: unable to retrieve existing invitations - http {response.status_code}")
        return False

    if response.status_code == 200:
        for invite in response.json():
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
        "invites": [
            username
        ],
        "groups": []
    }
    url = f"{config.sram_rest_api_url}/api/invitations/v1/collaboration_invites"
    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation put {url}: {payload}")

    response = requests.put(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"put_collaboration_invitation response: {response.status_code}")

    return response.status_code == 201


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

    return response.status_code == 201


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

    if new_role == 'manager':
        role = 'admin'
    else:
        role = 'member'

    payload = {
        "role": role,
        "uid": uuid
    }

    if config.sram_verbose_logging:
        log.write(ctx, f"update_collaboration_membership put {url}")

    response = requests.put(url, json=payload, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, f"update_collaboration_membership response: {response.status_code}")

    return response.status_code == 201


def get_co_members(ctx: rule.Context, co_identifier: str) -> List[str]:
    """Get SRAM Collaboration members.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier

    :returns: List of emails of the SRAM Collaboration members
    """
    if not misc.is_valid_uuid(co_identifier):
        log.write(ctx, f"get_co_members error: CO identifier is invalid {co_identifier}")
        return []

    url = f"{config.sram_rest_api_url}/api/collaborations/v1/{co_identifier}"

    if config.sram_verbose_logging:
        log.write(ctx, f"get_co_members get {url}")

    response = requests.get(url, headers=_request_headers(), timeout=30, verify=config.sram_tls_verify)
    if response.status_code != 200:
        if config.sram_verbose_logging:
            log.write(ctx, f"get_co_members response: {response.status_code}")
        return []

    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, f"get_co_members response: {data}")

    co_members = []
    for key in data['collaboration_memberships']:
        co_members.append(key['user']['email'])

    if config.sram_verbose_logging:
        log.write(ctx, f"get_co_members members: {co_members}")

    return co_members


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
