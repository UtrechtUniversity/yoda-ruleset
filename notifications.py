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
           'api_notifications_dismiss',
           'api_notifications_dismiss_all']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def set(ctx, actor, receiver, target, message):
    """Save user notification.

    :param ctx:      Combined type of a callback and rei struct
    :param actor:    Actor of notification message
    :param receiver: Receiving user of notification message
    :param target:   Target path of the notification
    :param message:  Notification message for user
    """
    if user.exists(ctx, receiver):
        timestamp = int(time.time())
        notification = {"timestamp": timestamp, "actor": actor, "target": target, "message": message}
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
            notification["actor"] = user.from_str(ctx, notification["actor"])[0]

            # Get data package and link from target path for research and vault packages.
            space, _, group, subpath = pathutil.info(notification["target"])
            if space is pathutil.Space.RESEARCH:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/research?dir=/{}/{}".format(group, subpath)
            elif space is pathutil.Space.VAULT:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/vault?dir=/{}/{}".format(group, subpath)

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


@api.make()
def api_notifications_dismiss_all(ctx):
    """Dismiss all user notifications.

    :param ctx: Combined type of a callback and rei struct
    """
    key = "{}_%".format(NOTIFICATION_KEY)
    user_name = user.full_name(ctx)
    ctx.uuUserMetaRemove(user_name, key, '', '')
