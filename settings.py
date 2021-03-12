# -*- coding: utf-8 -*-
"""Functions for user settings."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *
from util.query import Query

__all__ = ['api_settings_load',
           'api_settings_save']

# Allowed user settings should be synced with uuUserPolicyCanUserModify.
USER_SETTINGS = {"mail_notifications": {"default": True, "values": [True, False]}}


@api.make()
def api_settings_load(ctx):
    """Load user settings.

    :param ctx: Combined type of a callback and rei struct

    :returns: List with all settings
    """
    settings = [(a, v) for a, v
                in Query(ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, META_USER_ATTR_UNITS",
                              "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME like '{}'".format(user.name(ctx), "org_settings_"))]

    # Add defaults for missing settings.
    for setting in USER_SETTINGS:
        if setting not in settings:
            settings.append((setting, USER_SETTINGS[setting]["default"]))

    return settings


@api.make()
def api_settings_save(ctx, settings):
    """Save user settings.

    :param ctx:      Combined type of a callback and rei struct
    :param settings: List with settings to be saved

    :returns: API status
    """
    try:
        for a, v in settings.items():
            if a in USER_SETTINGS and v in USER_SETTINGS[a]["values"]:
                ctx.uuUserModify(user.full_name(ctx), a, str(v), '', '')

        return api.Result.ok()
    except Exception as e:
        return api.Error('internal', 'Saving settings failed. Please try again')
