# -*- coding: utf-8 -*-
"""Functions for communicating with SRAM and some utilities."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import random
import string
import json

import requests
import mail

from util import *


def sram_post_collaboration(ctx, payload):
    """Create SRAM Collaborative Organisation Identifier."""
    
    url = "{}/api/collaborations/v1".format(config.sram_rest_api_url)
    
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer '+ config.sram_api_key}

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    data = response.json()

    return data

def sram_get_uid(ctx, co_identifier, user_name, group_name):
    """Get SRAM Collaboration member uid."""

    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer '+ config.sram_api_key}

    response = requests.get(url, headers=headers, timeout=30)
    data = response.json()
    uid = ''
    for key in data['collaboration_memberships']:
        if key['user']['email'] == user_name.split('#')[0]:
            uid = key['user']['uid']

    return uid

def sram_delete_collaboration(ctx, co_identifier):
    """Delete SRAM Collaborative Organisation."""
    
    url = "{}/api/collaborations/v1/{}".format(config.sram_rest_api_url, co_identifier)
    
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer '+ config.sram_api_key}

    response = requests.delete(url, headers=headers, timeout=30)
    data = response.status_code

    return data


def sram_delete_collab_membership(ctx, co_identifier, uid):
    """Delete SRAM Collaborative Organisation membership."""
    
    url = "{}/api/collaborations/v1/{}/members/{}".format(config.sram_rest_api_url, co_identifier, uid)
    
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8', 'Authorization': 'bearer '+ config.sram_api_key}

    response = requests.delete(url, headers=headers, timeout=30)
    data = response.status_code

    return data


def invitation_mail_group_add_user(ctx, group_name, username, co_identifier):
    import session_vars
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
