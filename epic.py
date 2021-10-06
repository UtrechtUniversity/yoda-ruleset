# -*- coding: utf-8 -*-
"""Functions for communicating with EPIC and some utilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import uuid

import publication
from util import *

__all__ = ['rule_generate_uuid']


def generate_uuid(ctx):
    """Generate random ID for DOI."""
    randomuuid = str(uuid.uuid4())
    return randomuuid.upper()


rule_generate_uuid = rule.make(inputs=[], outputs=[0])(generate_uuid)


def register_epic_pid(ctx, target):
    """Create and try to register an EPIC PID.

    :param ctx:    Combined type of a callback and rei struct
    :param target: Target to register EPIC PID on

    :return: Dict with url, PID and http status.
    """
    config = publication.get_publication_config(ctx)
    host = config['davrodsVHost']
    parts = target.split('/')
    subpath = '/'.join(parts[2:])  # only user part without /tempZone/home
    url = "https://" + host + "/" + subpath

    pid = generate_uuid(ctx)

    ret = msi.register_epic_pid(ctx, url, pid, '')

    return {'url': ret['arguments'][0],
            'pid': ret['arguments'][1],
            'httpCode': ret['arguments'][2]}


def save_epic_pid(ctx, target, url, pid):
    """Save persistent EPIC ID.

    :param ctx:    Combined type of a callback and rei struct
    :param target: Target to register EPIC PID on
    :param url:    URL of EPIC PID
    :param pid:    PID of EPIC PID
    """
    avu.set_on_coll(ctx, target, constants.UUORGMETADATAPREFIX + "epic_url", url)
    avu.set_on_coll(ctx, target, constants.UUORGMETADATAPREFIX + "epic_pid", pid)
