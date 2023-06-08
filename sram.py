# -*- coding: utf-8 -*-
"""Functions for communicating with SRAM and some utilities."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import requests
import session_vars

import mail
from util import *


def sram_post_collaboration(payload):
    """Create SRAM Collaborative Organisation Identifier.

    :param payload: JSON object with required information

    :returns: JSON object with new collaboration details
    """

    url = "{}/api/collaborations/v1".format(config.sram_rest_api_url)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    response = requests.post(url, json=payload, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.json()

    return data


def sram_get_uid(co_identifier, user_name):
    """Get SRAM Collaboration member uid.

    :param co_identifier: SRAM CO identifier
    :param user_name: Name of the user

    :returns: Unique id of the user
    """

    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    response = requests.get(url, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.json()
    uid = ''
    for key in data['collaboration_memberships']:
        if key['user']['email'] == user_name.split('#')[0]:
            uid = key['user']['uid']

    return uid


def sram_delete_collaboration(co_identifier):
    """Delete SRAM Collaborative Organisation.

    :param co_identifier: SRAM CO identifier

    :returns: HTTP status code of the response
    """

    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    response = requests.delete(url, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.status_code

    return data


def sram_delete_collab_membership(co_identifier, uid):
    """Delete SRAM Collaborative Organisation membership.

    :param co_identifier: SRAM CO identifier
    :param uid: Unique id of the user

    :returns: HTTP status code of the response
    """

    url = "{}/api/collaborations/v1/{}/members/{}".format(config.sram_rest_api_url, co_identifier, uid)
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer ' + config.sram_api_key}

    response = requests.delete(url, headers=headers, timeout=30, verify=config.sram_tls_verify)
    data = response.status_code

    return data


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
