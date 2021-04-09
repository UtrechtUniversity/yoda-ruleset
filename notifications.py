# -*- coding: utf-8 -*-
"""Functions for user notifications."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import json
import time
from datetime import datetime

from util import *
from util.query import Query

__all__ = ['api_notifications_load',
           'api_notifications_dismiss']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def set(ctx, receiver, message):
    """Save user notification.

    :param ctx:      Combined type of a callback and rei struct
    :param receiver: Receiver of notification message
    :param message:  Notification message for user
    """
    if user.exists(ctx, receiver):
        timestamp = int(time.time())
        notification = {"timestamp": timestamp, "message": message}
        ctx.uuUserModify(receiver, "{}_{}".format(NOTIFICATION_KEY, str(timestamp)), json.dumps(notification), '', '')


@api.make()
def api_notifications_load(ctx):
    """Load user notifications.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with all notifications
    """
    results = [v for v
               in Query(ctx, "META_USER_ATTR_VALUE",
                             "USER_NAME = '{}' AND USER_TYPE = 'rodsuser' AND META_USER_ATTR_NAME like '{}_%%'".format(user.name(ctx), NOTIFICATION_KEY))]

    notifications = []
    for result in results:
        try:
            notification = jsonutil.parse(result)
            notification["datetime"] = (datetime.fromtimestamp(notification["timestamp"])).strftime('%Y-%m-%d %H:%M')
            notifications.append(notification)
        except Exception:
            continue

    # Return notifications sorted on timestamp
    return sorted(notifications, key=lambda k: k['timestamp'], reverse=True)


@api.make()
def api_notifications_dismiss(ctx, identifier):
    """Dismiss user notification.

    :param ctx:        Combined type of a callback and rei struct
    :param identifier: Identifier of notification message
    """
    key = "{}_{}".format(NOTIFICATION_KEY, str(identifier))
    user_name = user.full_name(ctx)
    ctx.uuUserMetaRemove(user_name, key, '', '')
