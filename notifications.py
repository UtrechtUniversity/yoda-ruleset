# -*- coding: utf-8 -*-
"""Functions for user notifications."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import json
import random
import string
import time
from datetime import datetime, timedelta

import genquery
from dateutil import relativedelta
from genquery import Query

import data_access_token
import folder
import mail
import settings
from util import *

__all__ = ['api_notifications_load',
           'api_notifications_dismiss',
           'api_notifications_dismiss_all',
           'rule_mail_notification_report',
           'rule_process_ending_retention_packages',
           'rule_process_groups_expiration_date',
           'rule_process_data_access_token_expiry']

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
        ctx.uuUserModify(receiver, "{}_{}".format(NOTIFICATION_KEY, identifier), json.dumps(notification), '', '')

        # Send mail notification if immediate notifications are on.
        receiver = user.from_str(ctx, receiver)[0]
        mail_notifications = settings.load(ctx, 'mail_notifications', username=receiver)
        if mail_notifications == "IMMEDIATE":
            send_notification(ctx, receiver, actor, message)


@api.make()
def api_notifications_load(ctx, sort_order="desc"):
    """Load user notifications.

    :param ctx:        Combined type of a callback and rei struct
    :param sort_order: Sort order of notifications on timestamp ("asc" or "desc", default "desc")

    :returns: Dict with all notifications
    """
    results = [v for v
               in Query(ctx, "META_USER_ATTR_VALUE",
                             "USER_NAME = '{}' AND USER_TYPE != 'rodsgroup' AND META_USER_ATTR_NAME like '{}_%%'".format(user.name(ctx), NOTIFICATION_KEY))]

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
            elif notification["target"] != "":
                notification["link"] = notification["target"]

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


def send_notification(ctx, to, actor, message):
    return mail.send(ctx,
                     to=to,
                     actor=actor,
                     subject='[Yoda] {}'.format(message),
                     body="""
You received a new notification: {}

Login to view all your notifications: https://{}/user/notifications
If you do not want to receive these emails, you can change your notification preferences here: https://{}/user/settings

Best regards,
Yoda system
""".format(message, config.yoda_portal_fqdn, config.yoda_portal_fqdn))


@rule.make(inputs=range(2), outputs=range(2, 4))
def rule_mail_notification_report(ctx, to, notifications):
    if not user.is_admin(ctx):
        return api.Error('not_allowed', 'Only rodsadmin can send test mail')

    return _wrapper(ctx,
                    to=to,
                    actor='system',
                    subject='[Yoda] {} notification(s)'.format(notifications),
                    body="""
You have {} notification(s).

Login to view all your notifications: https://{}/user/notifications
If you do not want to receive these emails, you can change your notification preferences here: https://{}/user/settings

Best regards,
Yoda system
""".format(notifications, config.yoda_portal_fqdn, config.yoda_portal_fqdn))


@rule.make()
def rule_process_ending_retention_packages(ctx):
    """Rule interface for checking vault packages for ending retention.

    :param ctx: Combined type of a callback and rei struct
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "retention - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'retention - Checking Vault packages for ending retention')

    zone = user.zone(ctx)
    errors = 0
    dp_notify_count = 0

    # Retrieve all data packages in this vault.
    iter = genquery.row_iterator(
        "COLL_NAME",
        "META_COLL_ATTR_NAME = 'org_vault_status' AND COLL_NAME not like '%/original'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        dp_coll = row[0]
        meta_path = meta.get_latest_vault_metadata_path(ctx, dp_coll)

        # Try to load the metadata file.
        try:
            metadata = jsonutil.read(ctx, meta_path)
            current_schema_id = meta.metadata_get_schema_id(metadata)
            if current_schema_id is None:
                log.write(ctx, 'retention - Schema id missing - Please check the structure of this file. <{}>'.format(dp_coll))
                errors += 1
                continue
        except jsonutil.ParseError:
            log.write(ctx, 'retention - JSON invalid - Please check the structure of this file. <{}>'.format(dp_coll))
            errors += 1
            continue
        except msi.Error as e:
            log.write(ctx, 'retention - The metadata file could not be read. ({}) <{}>'.format(e, dp_coll))
            errors += 1
            continue

        # Get deposit date and end preservation date based upon retention period.
        iter2 = genquery.row_iterator(
            "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + dp_coll + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
            genquery.AS_LIST, ctx
        )
        for row2 in iter2:
            # row2 contains json encoded [str(int(time.time())), action, actor]
            log_item_list = jsonutil.parse(row2[1])
            if log_item_list[1] == "submitted for vault":
                deposit_timestamp = datetime.fromtimestamp(int(log_item_list[0]))
                date_deposit = deposit_timestamp.date()
                break

        try:
            retention = int(metadata['Retention_Period'])
        except KeyError:
            log.write(ctx, 'retention - No retention period set in metadata. <{}>'.format(dp_coll))
            continue

        try:
            date_end_retention = date_deposit.replace(year=date_deposit.year + retention)
        except ValueError:
            log.write(ctx, 'retention - Could not determine retention end date. Retention period: <{}>'.format(retention))
            continue

        r = relativedelta.relativedelta(date_end_retention, datetime.now().date())
        formatted_date = date_end_retention.strftime('%Y-%m-%d')

        log.write(ctx, 'retention - Retention period ({} years) ending in {} years, {} months and {} days ({}): <{}>'.format(retention, r.years, r.months, r.days, formatted_date, dp_coll))
        if r.years == 0 and r.months <= 1:
            group_name = folder.collection_group_name(ctx, dp_coll)
            category = group.get_category(ctx, group_name)
            datamanager_group_name = "datamanager-" + category

            if group.exists(ctx, datamanager_group_name):
                dp_notify_count += 1
                # Send notifications to datamanager(s).
                datamanagers = folder.get_datamanagers(ctx, '/{}/home/'.format(zone) + datamanager_group_name)
                message = "Data package reaching end of preservation date: {}".format(formatted_date)
                for datamanager in datamanagers:
                    datamanager = '{}#{}'.format(*datamanager)
                    actor = 'system'
                    set(ctx, actor, datamanager, dp_coll, message)
                log.write(ctx, 'retention - Notifications set for ending retention period on {}. <{}>'.format(formatted_date, dp_coll))

    log.write(ctx, 'retention - Finished checking vault packages for ending retention | notified: {} | errors: {}'.format(dp_notify_count, errors))


@rule.make()
def rule_process_groups_expiration_date(ctx):
    """Rule interface for checking research groups for reaching group expiration date.

    :param ctx: Combined type of a callback and rei struct
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "retention - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'retention - Checking research groups for reaching group expiration date')

    zone = user.zone(ctx)
    notify_count = 0
    today = datetime.now().strftime('%Y-%m-%d')

    # First query: obtain a list of groups with group attributes
    # and group retention period less or equal than today
    # and group retention != '.' (actually meaning empty)
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND USER_GROUP_NAME like 'research-%' AND META_USER_ATTR_NAME = 'expiration_date'"
        " AND META_USER_ATTR_VALUE <= '{}'  AND META_USER_ATTR_VALUE != '.'".format(today),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        group_name = row[0]
        coll = '/{}/home/{}'.format(zone, group_name)
        expiration_date = row[2]

        # find corresponding datamanager
        category = group.get_category(ctx, group_name)
        datamanager_group_name = "datamanager-" + category
        if group.exists(ctx, datamanager_group_name):
            notify_count += 1
            # Send notifications to datamanager(s).
            datamanagers = folder.get_datamanagers(ctx, '/{}/home/'.format(zone) + datamanager_group_name)
            message = "Group '{}' reached expiration date: {}".format(group_name, expiration_date)

            for datamanager in datamanagers:
                datamanager = '{}#{}'.format(*datamanager)
                actor = 'system'
                set(ctx, actor, datamanager, coll, message)
            log.write(ctx, 'retention - Notifications set for group {} reaching expiration date on {}. <{}>'.format(group_name, expiration_date, coll))

    log.write(ctx, 'retention - Finished checking research groups for reaching group expiration date | notified: {}'.format(notify_count))


@rule.make()
def rule_process_data_access_token_expiry(ctx):
    """Rule interface for checking for data access tokens that are expiring soon.

    :param ctx: Combined type of a callback and rei struct
    """
    # Only send notifications if expiration notifications are enabled.
    if config.token_expiration_notification == 0:
        return

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "data access token - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'data access token - Checking for expiring data access tokens')
    tokens = data_access_token.get_all_tokens(ctx)
    for token in tokens:
        # Calculate token expiration notification date.
        exp_time = datetime.strptime(token['exp_time'], '%Y-%m-%d %H:%M:%S.%f')
        date_exp_time = exp_time - timedelta(hours=config.token_expiration_notification)
        r = relativedelta.relativedelta(date_exp_time, datetime.now().date())

        # Send notification if token expires in less than a day.
        if r.years == 0 and r.months == 0 and r.days <= 1:
            actor = 'system'
            target = str(user.from_str(ctx, token['user']))
            message = "Data access password with label <{}> is expiring".format(token["label"])
            set(ctx, actor, target, "/user/data_access", message)
            log.write(ctx, 'data access token - Notification set for expiring data access token from user <{}>'.format(token["user"]))
    log.write(ctx, 'data access token - Finished checking for expiring data access tokens')
