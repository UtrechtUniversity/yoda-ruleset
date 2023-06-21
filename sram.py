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

    # Build SRAM payload.
    payload = {
        "name": 'yoda-' + group_name,
        "short_name": group_name,
        "description": description,
        "disable_join_requests": False,
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
