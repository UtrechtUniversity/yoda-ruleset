# -*- coding: utf-8 -*-
"""Functions for user notifications."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import base64
import json
import random
import string
import time
from datetime import datetime

import genquery
from genquery import Query

import mail
import settings
from util import *

__all__ = ['api_notifications_load',
           'api_notifications_dismiss',
           'api_notifications_dismiss_all']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def generate_random_id(ctx):
    """Generate random ID for notification."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for x in range(10))


def set(ctx, actor, receiver, target, message):
    """Set user notification and send mail notification when configured.

    :param ctx:      Combined type of a callback and rei struct
    :param actor:    Actor of notification message
    :param receiver: Receiving user of notification message
    :param target:   Target path of the notification
    :param message:  Notification message for user
    """
    if user.exists(ctx, receiver):
        identifier = generate_random_id(ctx)
        timestamp = int(time.time())
        notification = {"identifier": identifier, "timestamp": timestamp, "actor": actor, "target": target, "message": message}
        ctx.uuAdminUserModify(receiver, "{}_{}".format(NOTIFICATION_KEY, identifier), str(base64.b64encode(bytes(json.dumps(notification), "utf-8")), "utf-8"))

        # Send mail notification if immediate notifications are on.
        receiver = user.from_str(ctx, receiver)[0]
        mail_notifications = settings.load(ctx, 'mail_notifications', username=receiver)
        if mail_notifications == "IMMEDIATE":
            mail.notification(ctx, receiver, actor, message)


@api.make()
def api_notifications_load(ctx, sort_order="desc"):
    """Load user notifications.

    :param ctx:        Combined type of a callback and rei struct
    :param sort_order: Sort order of notifications on timestamp ("asc" or "desc", default "desc")

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
                notification["link"] = "/research/browse?dir=/{}/{}".format(group, subpath)
            elif space is pathutil.Space.VAULT:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/vault/browse?dir=/{}/{}".format(group, subpath)

                # Deposit situation required different information to be presented.
                if subpath.startswith('deposit-'):
                    data_package_reference = ""
                    iter = genquery.row_iterator(
                        "META_COLL_ATTR_VALUE",
                        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(notification["target"], constants.DATA_PACKAGE_REFERENCE),
                        genquery.AS_LIST, ctx
                    )

                    for row in iter:
                        data_package_reference = row[0]

                    deposit_title = '(no title)'
                    iter = genquery.row_iterator(
                        "META_COLL_ATTR_VALUE",
                        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'Title'".format(notification["target"]),
                        genquery.AS_LIST, ctx
                    )
                    for row in iter:
                        deposit_title = row[0]

                    notification["data_package"] = deposit_title
                    notification["link"] = "/vault/yoda/{}".format(data_package_reference)

                    # Find real actor when
                    if notification["actor"] == 'system':
                        # Get actor from action log on action = "submitted for vault"
                        iter2 = genquery.row_iterator(
                            "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
                            "COLL_NAME = '" + notification["target"] + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
                            genquery.AS_LIST, ctx
                        )
                        for row2 in iter2:
                            # row2 contains json encoded [str(int(time.time())), action, actor]
                            log_item_list = jsonutil.parse(row2[1])
                            if log_item_list[1] == "submitted for vault":
                                notification["actor"] = log_item_list[2].split('#')[0]
                                break

            notifications.append(notification)
        except Exception:
            continue

    # Return notifications sorted on timestamp
    if sort_order == "asc":
        return sorted(notifications, key=lambda k: k['timestamp'], reverse=False)
    else:
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
