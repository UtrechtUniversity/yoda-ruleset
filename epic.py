# -*- coding: utf-8 -*-
"""Functions for communicating with EPIC and some utilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import uuid

from util import *

__all__ = ['rule_generate_uuid']


def generate_uuid(ctx):
    """Generate random ID for DOI."""
    randomuuid = str(uuid.uuid4())
    return randomuuid.upper()


rule_generate_uuid = rule.make(inputs=[], outputs=[0])(generate_uuid)


def register_epic_pid(ctx, target):
    """ create and try to register an EPIC PID 
        param[in]  target
        param[out] url
        param[out] pid
        param[out] httpCode
    """

    config = get_publication_config(ctx)
    host = config['davrodsVHost']
    parts = target.split('/')  
    subpath = '/'.join(parts[2:]) # only user part without /tempZone/home
    url = "https://" + host + "/" + subpath

    pid = generate_uuid(ctx)

    ret = msi.register_epic_pid(ctx, url, pid, '')
    httpCode =  ret['arguments'][2]

    return {'url': ret['arguments'][0],
            'pid': ret['arguments'][1],
            'httpCode': ret['arguments'][2]}


def save_epic_pid(ctx, target, url, pid):
    """ save persistent EPIC ID """

    avu.set_on_coll(ctx, target, constants.UUORGMETADATAPREFIX + "epic_url", url)
    avu.set_on_coll(ctx, target, constants.UUORGMETADATAPREFIX + "epic_pid", pid)


def get_publication_config(ctx):
    """ Get all publication config keys and their values 
        Report any missing keys
    """
    zone = user.zone(ctx)
    system_coll = "/" + zone + constants.UUSYSTEMCOLLECTION

    attr2keys = {"public_host": "publicHost",
            "public_vhost": "publicVHost",
            "moai_host": "moaiHost",
            "yoda_prefix": "yodaPrefix",
            "datacite_prefix": "dataCitePrefix",
            "random_id_length": "randomIdLength",
            "yoda_instance": "yodaInstance",
            "davrods_vhost": "davrodsVHost",
            "davrods_anonymous_vhost": "davrodsAnonymousVHost"}
    configKeys = {}
    found_attrs = []

    prefix_length = len(constants.UUORGMETADATAPREFIX)
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + system_coll + "' AND  META_COLL_ATTR_NAME like '" + constants.UUORGMETADATAPREFIX + "%'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # Strip prefix From attribute names
        attr = row[0][prefix_length:]
        val = row[1]

        try:
            found_attrs.append(attr)
            configKeys[attr2keys[attr]] = val
        except KeyError:
            continue

    # Any differences between 
    if len(found_attrs) != len(attr2keys):
        # Difference between attrs wanted and found
        for key in attr2keys:
            if not key in found_attrs:
                log.write(ctx, 'Missing config key ' + key)
    
    return configKeys
