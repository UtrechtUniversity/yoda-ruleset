# -*- coding: utf-8 -*-
"""Functions for user settings."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *
from util.query import Query

__all__ = ['api_settings_load',
           'api_settings_save']

USER_SETTINGS = {"mail_notifications": {"default": True, "values": [True, False]}}


@api.make()
def api_settings_load(ctx):
    """Load user settings.

    :param ctx: Combined type of a callback and rei struct

    :returns: List with all settings
    """
    settings = [(k, v) for k, v
                in Query(ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, META_USER_ATTR_UNITS",
                              "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME like '{}'".format(user.name(ctx), "org_settings_"))]

    # Add defaults for missing settings.
    for setting in USER_SETTINGS:
        if setting not in settings:
            settings.append((setting, USER_SETTINGS[setting]["default"]))

    return settings


@api.make()
def api_settings_save(ctx, settings):
    """Load user settings.

    :param ctx:      Combined type of a callback and rei struct
    :param settings: List with settings to be saved

    :returns: API status
    """
    for k, v in settings.items():
        if k in USER_SETTINGS and v in USER_SETTINGS[k]["values"]:
            log.debug(ctx, "SAVE SETTING: {}: {}".format(k, v))

    return {}
