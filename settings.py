# -*- coding: utf-8 -*-
"""Functions for user settings."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *
from util.query import Query

__all__ = ['api_settings_load',
           'api_settings_save']

# Allowed settings should be synchronised with uuUserPolicyCanUserModify.
USER_SETTINGS = {"mail_notifications": {"default": "True", "values": ["True", "False"]}}
SETTINGS_KEY = constants.UUORGMETADATAPREFIX + "settings_"


@api.make()
def api_settings_load(ctx):
    """Load user settings.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with all settings
    """
    settings = dict([(a.replace(SETTINGS_KEY, ""), v) for a, v
                     in Query(ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
                                   "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME like '{}%%'".format(user.name(ctx), SETTINGS_KEY))])

    # Add defaults for missing settings.
    for setting in USER_SETTINGS:
        if setting not in settings:
            settings.append((setting, USER_SETTINGS[setting]["default"]))

    return settings


@api.make()
def api_settings_save(ctx, settings):
    """Save user settings.

    :param ctx:      Combined type of a callback and rei struct
    :param settings: Dict with settings to be saved

    :returns: API status
    """
    for a, v in settings.items():
        if a in USER_SETTINGS and v in USER_SETTINGS[a]["values"]:
            try:
                ctx.uuUserModify(user.full_name(ctx), "{}{}".format(SETTINGS_KEY, a), str(v), '', '')
            except Exception as e:
                return api.Error('internal', 'Saving settings failed. Please try again')

    return api.Result.ok()
