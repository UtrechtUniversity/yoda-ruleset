# -*- coding: utf-8 -*-
"""Functions for communicating with SRAM and some utilities."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import datetime
import time

import requests
import session_vars

import mail
from util import *


def sram_post_collaboration(ctx, group_name, description, expiration_date):
    """Create SRAM Collaborative Organisation Identifier.

    :param ctx:             Combined type of a callback and rei struct
    :param group_name:      Name of the group to create
    :param description:     Description of the group to create
    :param expiration_date: Retention period for the group

    :returns: JSON object with new collaboration details
    """
    url = "{}/api/collaborations/v1".format(config.sram_rest_api_url)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    if expiration_date == '':
        # Now plus a year.
        expiration_date = datetime.datetime.fromtimestamp(int(time.time() + 3600 * 24 * 365)).strftime('%Y-%m-%d')

    # Get epoch expiry date.
    date = datetime.datetime.strptime(expiration_date, "%Y-%m-%d")
    epoch = datetime.datetime.utcfromtimestamp(0)
    epoch_date = int((date - epoch).total_seconds())

    # Create unique short name of group
    short_name = group.unique_short_name(ctx, group_name)

    disable_join_requests = True
    if config.sram_flow == 'join_request':
        disable_join_requests = False

    # Build SRAM payload.
    payload = {
        "name": 'yoda-' + group_name,
        "short_name": short_name,
        "description": description,
        "disable_join_requests": disable_join_requests,
        "disclose_member_information": True,
        "disclose_email_information": True,
        "expiry_date": epoch_date,
        "administrators": [session_vars.get_map(ctx.rei)["client_user"]["user_name"]]
    }

    if config.sram_verbose_logging:
        log.write(ctx, "post {}: {}".format(url, payload))

    response = requests.post(url, json=payload, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(data))

    return data


def sram_get_uid(ctx, co_identifier, user_name):
    """Get SRAM Collaboration member uid.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param user_name:     Name of the user

    :returns: Unique id of the user
    """
    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    if config.sram_verbose_logging:
        log.write(ctx, "get {}".format(url))

    response = requests.get(url, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.json()

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(data))

    uid = ''
    for key in data['collaboration_memberships']:
        if key['user']['email'] == user_name.split('#')[0]:
            uid = key['user']['uid']

    if config.sram_verbose_logging:
        log.write(ctx, "user_name: {}, uuid: {}".format(user_name.split('#')[0], uid))

    return uid


def sram_delete_collaboration(ctx, co_identifier):
    """Delete SRAM Collaborative Organisation.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier

    :returns: Boolean indicating of deletion of collaboration succeeded
    """
    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    if config.sram_verbose_logging:
        log.write(ctx, "post {}".format(url))

    response = requests.delete(url, headers=headers, timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(response.status_code))

    return response.status_code == 204


def sram_delete_collaboration_membership(ctx, co_identifier, uuid):
    """Delete SRAM Collaborative Organisation membership.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param uuid:          Unique id of the user

    :returns: Boolean indicating of deletion of collaboration membership succeeded
    """
    url = "{}/api/collaborations/v1/{}/members/{}".format(config.sram_rest_api_url, co_identifier, uuid)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    if config.sram_verbose_logging:
        log.write(ctx, "post {}".format(url))

    response = requests.delete(url, headers=headers, timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(response.status_code))

    return response.status_code == 204


def sram_put_collaboration_invitation(ctx, group_name, username, co_identifier):
    """Create SRAM Collaborative Organisation Identifier.

    :param ctx:           Combined type of a ctx and rei struct
    :param group_name:    Name of the group the user is to invited to join
    :param username:      Name of the user to be invited
    :param co_identifier: SRAM identifier of the group the user is to invited to join

    :returns: Boolean indicating if put of new collaboration invitation succeeded
    """
    url = "{}/api/invitations/v1/collaboration_invites".format(config.sram_rest_api_url)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    # Now plus a year.
    expiration_date = datetime.datetime.fromtimestamp(int(time.time() + 3600 * 24 * 365)).strftime('%Y-%m-%d')

    # Get epoch expiry date.
    date = datetime.datetime.strptime(expiration_date, "%Y-%m-%d")
    epoch = datetime.datetime.utcfromtimestamp(0)
    epoch_date = int((date - epoch).total_seconds()) * 1000

    # Build SRAM payload.
    payload = {
        "collaboration_identifier": co_identifier,
        "message": "Invitation to join Yoda group {}".format(group_name),
        "intended_role": "member",
        "invitation_expiry_date": epoch_date,
        "invites": [
            username
        ],
        "groups": []
    }

    if config.sram_verbose_logging:
        log.write(ctx, "put {}: {}".format(url, payload))

    response = requests.put(url, json=payload, headers=headers, timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(response.status_code))

    return response.status_code == 201


def sram_connect_service_collaboration(ctx, group_name):
    """Connect a service to an existing SRAM collaboration.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group

    :returns: Boolean indicating if connecting a service to an existing collaboration succeeded
    """
    url = "{}/api/collaborations_services/v1/connect_collaboration_service".format(config.sram_rest_api_url)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    # Create unique short name of group
    short_name = group.unique_short_name(ctx, group_name)

    # Build SRAM payload.
    payload = {
        "short_name": short_name,
        "service_entity_id": config.sram_service_entity_id
    }

    if config.sram_verbose_logging:
        log.write(ctx, "put {}: {}".format(url, payload))

    response = requests.put(url, json=payload, headers=headers, timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(response.status_code))

    return response.status_code == 201


def invitation_mail_group_add_user(ctx, group_name, username, co_identifier):
    """Send invitation email to newly added user to the group.

    :param ctx: Combined type of a ctx and rei struct
    :param group_name: Name of the group the user is to invited to join
    :param username: Name of the user to be invited
    :param co_identifier: SRAM identifier of the group included in the invitation link

    :returns: Sends the invitation mail to the user
    """

    return mail.send(ctx,
                     to=username,
                     cc='',
                     actor=user.full_name(ctx),
                     subject=(u"Invitation to join collaboration {}".format(group_name)),
                     body="""Dear {},

You have been invited by {} to join a collaboration page.

The following link will take you directly to SRAM: {}/registration?collaboration={}

With kind regards,
Yoda
""".format(username.split('@')[0], session_vars.get_map(ctx.rei)["client_user"]["user_name"], config.sram_rest_api_url, co_identifier))


def sram_update_collaboration_membership(ctx, co_identifier, uuid, new_role):
    """Update SRAM Collaborative Organisation membership.

    :param ctx:           Combined type of a callback and rei struct
    :param co_identifier: SRAM CO identifier
    :param uuid:          Unique id of the user
    :param new_role:      New role of the user

    :returns: Boolean indicating that updation of collaboration membership succeeded
    """
    url = "{}/api/collaborations/v1/{}/members".format(config.sram_rest_api_url, co_identifier)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    if new_role == 'manager':
        role = 'admin'
    else:
        role = 'member'

    payload = {
        "role": role,
        "uid": uuid
    }

    if config.sram_verbose_logging:
        log.write(ctx, "put {}".format(url))

    response = requests.put(url, json=payload, headers=headers, timeout=30, verify=config.sram_tls_verify)

    if config.sram_verbose_logging:
        log.write(ctx, "response: {}".format(response.status_code))

    return response.status_code == 201
