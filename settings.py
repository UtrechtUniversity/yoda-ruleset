# -*- coding: utf-8 -*-
"""Functions for user settings."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['api_settings_load',
           'api_settings_save']


@api.make()
def api_settings_load(ctx):
    """Load user settings.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with all settings
    """
    return {}


@api.make()
def api_settings_save(ctx, settings):
    """Load user settings.

    :param ctx:      Combined type of a callback and rei struct
    :param settings: Dictionary with settings to be saved

    :returns: API status
    """
    return {}
