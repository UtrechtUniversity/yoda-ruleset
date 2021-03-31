# -*- coding: utf-8 -*-
"""Functions for user notifications."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import time

from util import *
from util.query import Query

__all__ = ['api_notifications_load']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def set(ctx, receiver, message):
    """Save user notification.

    :param ctx:      Combined type of a callback and rei struct
    :param receiver: Receiver of notification message
    :param message:  Notification message for user
    """
    notification = {"timestamp": str(int(time.time())), "message": message}
    ctx.uuUserModify(receiver, NOTIFICATION_KEY, json.dumps(notification), '', '')


@rule.make(inputs=[0, 1], outputs=[2])
def rule_notification_set(ctx, receiver, message):
    """Rule interface for setting notification (testing only).

    :param ctx:      Combined type of a callback and rei struct
    :param receiver: Receiver of notification message
    :param message:  Notification message for user
    """
    set(ctx, receiver, message)


@api.make()
def api_notifications_load(ctx):
    """Load user notifications.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with all notifications
    """
    result = [v for v
              in Query(ctx, "META_USER_ATTR_VALUE",
                            "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME = '{}'".format(user.name(ctx), NOTIFICATION_KEY))]
    notifications = []
    for notification in result:
        notifications.append(jsonutil.parse(notification))

    return notifications
