# -*- coding: utf-8 -*-
"""Functions for user notifications."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *
from util.query import Query

__all__ = ['api_notifications_load']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def set(ctx, notification):
    """Save user settings.

    :param ctx:          Combined type of a callback and rei struct
    :param notification: Notification message for user
    """
    ctx.uuUserModify(user.full_name(ctx), NOTIFICATION_KEY, str(notification), '', '')


@api.make()
def api_notifications_load(ctx):
    """Load user notifications.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with all notifications
    """
    return {v for v
            in Query(ctx, "META_USER_ATTR_VALUE",
                          "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME = '{}'".format(user.name(ctx), NOTIFICATION_KEY))}
