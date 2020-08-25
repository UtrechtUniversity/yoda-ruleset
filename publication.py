# -*- coding: utf-8 -*-
"""Functions for publication."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *


def get_publication_config(ctx):
    """Get all publication config keys and their values and report any missing keys."""
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
            if key not in found_attrs:
                log.write(ctx, 'Missing config key ' + key)

    return configKeys
