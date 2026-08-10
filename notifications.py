"""Functions for user notifications."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2021-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import random
import string
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Tuple

import genquery
from dateutil import relativedelta
from genquery import Query
from tstrings import t

import data_access_token
import folder
import mail
import meta
import settings
from util import *

__all__ = ['api_notifications_load',
           'api_notifications_dismiss',
           'api_notifications_dismiss_all',
           'rule_mail_notification_report',
           'rule_process_ending_retention_packages',
           'rule_process_groups_expiration_date',
           'rule_process_inactive_research_groups',
           'rule_process_data_access_token_expiry']

NOTIFICATION_KEY = constants.UUORGMETADATAPREFIX + "notification"


def generate_random_id(ctx: rule.Context) -> str:
    """Generate random ID for notification."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for x in range(10))


def set(ctx: rule.Context, actor: str, receiver: str, target: str, message: str) -> None:
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
        ctx.uuUserModify(receiver, f"{NOTIFICATION_KEY}_{identifier}", json.dumps(notification), '', '')

        # Send mail notification if immediate notifications are on.
        receiver = user.from_str(ctx, receiver)[0]
        mail_notifications = settings.load(ctx, 'mail_notifications', username=receiver)
        if mail_notifications == "IMMEDIATE":
            send_notification(ctx, receiver, actor, message)


@api.make()
def api_notifications_load(ctx: rule.Context, sort_order: str = "desc") -> List:
    """Load user notifications.

    :param ctx:        Combined type of a callback and rei struct
    :param sort_order: Sort order of notifications on timestamp ("asc" or "desc", default "desc")

    :returns: List with all notifications
    """
    results = list(Query(ctx, "META_USER_ATTR_VALUE",
                              f"USER_NAME = '{user.name(ctx)}' AND USER_TYPE != 'rodsgroup' AND META_USER_ATTR_NAME like '{NOTIFICATION_KEY}_%%'"))

    notifications = []
    for result in results:
        try:
            notification = jsonutil.parse(result)
            notification["datetime"] = (datetime.fromtimestamp(notification["timestamp"])).strftime('%Y-%m-%d %H:%M')
            notification["actor"] = user.from_str(ctx, notification["actor"])[0]

            # Get data package and link from target path for research, deposit and vault packages.
            space, _, group, subpath = pathutil.info(notification["target"])
            if space is pathutil.Space.RESEARCH:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/research/browse?dir=" + urllib.parse.quote(f"/{group}/{subpath}")
            elif space is pathutil.Space.DEPOSIT:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/deposit/data?dir=" + urllib.parse.quote(f"/{group}/{subpath}")
            elif space is pathutil.Space.VAULT:
                notification["data_package"] = group if subpath == '' else pathutil.basename(subpath)
                notification["link"] = "/vault/browse?dir=" + urllib.parse.quote(f"/{group}/{subpath}")

                # Deposit situation required different information to be presented.
                if subpath.startswith('deposit-'):
                    data_package_reference = ""
                    iter = genquery.row_iterator(
                        "META_COLL_ATTR_VALUE",
                        t("COLL_NAME = '{notification['target']}' AND META_COLL_ATTR_NAME = '{constants.DATA_PACKAGE_REFERENCE}'"),
                        genquery.AS_LIST, ctx
                    )

                    for row in iter:
                        data_package_reference = row[0]

                    deposit_title = '(no title)'
                    iter = genquery.row_iterator(
                        "META_COLL_ATTR_VALUE",
                        t("COLL_NAME = '{notification['target']}' AND META_COLL_ATTR_NAME = 'Title'"),
                        genquery.AS_LIST, ctx
                    )
                    for row in iter:
                        deposit_title = row[0]

                    notification["data_package"] = deposit_title
                    notification["link"] = f"/vault/yoda/{data_package_reference}"

                    # Find real actor when
                    if notification["actor"] == 'system':
                        # Get actor from action log on action = "submitted for vault"
                        iter2 = genquery.row_iterator(
                            "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
                            t("COLL_NAME = '{notification['target']}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}action_log'"),
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
def api_notifications_dismiss(ctx: rule.Context, identifier: str) -> api.Result:
    """Dismiss user notification.

    :param ctx:        Combined type of a callback and rei struct
    :param identifier: Identifier of notification message
    """
    user_name = user.name(ctx)
    key = f"{NOTIFICATION_KEY}_{identifier}"
    value = avu.get_attr_val_of_user(ctx, user_name, key)
    msi.sudo_obj_meta_remove(ctx, user_name, "-u", "", key, value, "", "")


@api.make()
def api_notifications_dismiss_all(ctx: rule.Context) -> api.Result:
    """Dismiss all user notifications.

    :param ctx: Combined type of a callback and rei struct
    """
    user_name = user.name(ctx)
    key = f"{NOTIFICATION_KEY}_%"

    # Retrieve list of notification AVUs of user.
    avus = list(genquery.Query(
        ctx, "META_USER_ATTR_NAME, META_USER_ATTR_VALUE, META_USER_ATTR_UNITS",
        f"USER_NAME = '{user_name}' AND USER_TYPE != 'rodsgroup' AND META_USER_ATTR_NAME like '{key}'")
    )

    # Remove notification AVUs.
    for (attr, value, unit) in avus:
        msi.sudo_obj_meta_remove(ctx, user_name, "-u", "", attr, value, unit, "")


def send_notification(ctx: rule.Context, to: str, actor: str, message: str) -> api.Result:
    return mail.send(ctx,
                     to=to,
                     actor=actor,
                     subject=f'[Yoda] {message}',
                     body=f"""
You received a new notification: {message}

Login to view all your notifications: https://{config.yoda_portal_fqdn}/user/notifications
If you do not want to receive these emails, you can change your notification preferences here: https://{config.yoda_portal_fqdn}/user/settings

Best regards,
Yoda system
""")


@rule.make(inputs=[0, 1], outputs=[2, 3])
def rule_mail_notification_report(ctx: rule.Context, to: str, notifications: str) -> Tuple[str, str]:
    if not user.is_rodsadmin(ctx):
        return '0', 'Only rodsadmin can send test mail'

    return mail.wrapper(ctx,
                        to=to,
                        actor='system',
                        subject=f'[Yoda] {notifications} notification(s)',
                        body=f"""
You have {notifications} notification(s).

Login to view all your notifications: https://{config.yoda_portal_fqdn}/user/notifications
If you do not want to receive these emails, you can change your notification preferences here: https://{config.yoda_portal_fqdn}/user/settings

Best regards,
Yoda system
""")


@rule.make()
def rule_process_ending_retention_packages(ctx: rule.Context) -> None:
    """Rule interface for checking vault packages for ending retention.

    :param ctx: Combined type of a callback and rei struct
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "retention - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'retention - Checking Vault packages for ending retention')

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

        if not pathutil.is_archived_datapackage_path(dp_coll):
            # This is not a top-level collection of an archived data package. Skip it.
            continue

        meta_path = meta.get_latest_vault_metadata_path(ctx, dp_coll)

        if meta_path is None:
            log.write(ctx, f"retention - No metadata found for data package <{dp_coll}>. Skipping it")
            continue

        # Try to load the metadata file.
        try:
            metadata = jsonutil.read(ctx, meta_path)
            current_schema_id = meta.metadata_get_schema_id(metadata)
            if current_schema_id is None:
                log.write(ctx, f'retention - Schema id missing - Please check the structure of this file. <{dp_coll}>')
                errors += 1
                continue
        except jsonutil.ParseError:
            log.write(ctx, f'retention - JSON invalid - Please check the structure of this file. <{dp_coll}>')
            errors += 1
            continue
        except msi.Error as e:
            log.write(ctx, f'retention - The metadata file could not be read. ({e}) <{dp_coll}>')
            errors += 1
            continue

        # Get deposit date and end preservation date based upon retention period.
        iter2 = genquery.row_iterator(
            "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
            t("COLL_NAME = '{dp_coll}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}action_log'"),
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
            log.write(ctx, f'retention - No retention period set in metadata. <{dp_coll}>')
            continue

        try:
            date_end_retention = date_deposit.replace(year=date_deposit.year + retention)
        except ValueError:
            log.write(ctx, f'retention - Could not determine retention end date. Retention period: <{retention}>')
            continue

        r = relativedelta.relativedelta(date_end_retention, datetime.now().date())
        formatted_date = date_end_retention.strftime('%Y-%m-%d')

        log.write(ctx, f'retention - Retention period ({retention} years) ending in {r.years} years, {r.months} months and {r.days} days ({formatted_date}): <{dp_coll}>')
        if r.years == 0 and r.months <= 1:
            try:
                datamanagers = folder.get_datamanagers(ctx, dp_coll)
            except ValueError as e:
                log.write(ctx, f"Unable to send retention time notifications for <{dp_coll}>: cannot get data managers: {str(e)}")
                datamanagers = []

            if len(datamanagers) > 0:
                dp_notify_count += 1
                # Send notifications to datamanager(s).
                message = f"Data package reaching end of preservation date: {formatted_date}"
                for datamanager in datamanagers:
                    datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
                    actor = 'system'
                    set(ctx, actor, datamanager_name, dp_coll, message)
                log.write(ctx, f'retention - Notifications set for ending retention period on {formatted_date}. <{dp_coll}>')

    log.write(ctx, f'retention - Finished checking vault packages for ending retention | notified: {dp_notify_count} | errors: {errors}')


@rule.make()
def rule_process_groups_expiration_date(ctx: rule.Context) -> None:
    """Rule interface for checking research groups for reaching group expiration date.

    :param ctx: Combined type of a callback and rei struct
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "group expiration date - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'group expiration date - Checking research groups for reaching group expiration date')

    zone = user.zone(ctx)
    notify_count = 0
    today = datetime.now().strftime('%Y-%m-%d')

    # First query: obtain a list of groups with group attributes
    # and group expiration date less or equal than today
    # and group expiration date != '.' (actually meaning empty)
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND USER_GROUP_NAME like 'research-%' AND META_USER_ATTR_NAME = 'expiration_date'"
        f" AND META_USER_ATTR_VALUE <= '{today}'  AND META_USER_ATTR_VALUE != '.'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        group_name = row[0]
        coll = f'/{zone}/home/{group_name}'
        expiration_date = row[2]

        try:
            datamanagers = folder.get_datamanagers(ctx, coll)
        except ValueError as e:
            log.write(ctx, f"Unable to send expiry time notifications for <{coll}>: cannot get data managers: {str(e)}")
            datamanagers = []

        if len(datamanagers) > 0:
            notify_count += 1
            # Send notifications to datamanager(s).
            message = f"Group '{group_name}' reached expiration date: {expiration_date}"

            for datamanager in datamanagers:
                datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
                actor = 'system'
                set(ctx, actor, datamanager_name, coll, message)
            log.write(ctx, f'group expiration date - Notifications set for group {group_name} reaching expiration date on {expiration_date}. <{coll}>')

    log.write(ctx, f'group expiration date - Finished checking research groups for reaching group expiration date | notified: {notify_count}')


@rule.make()
def rule_process_inactive_research_groups(ctx: rule.Context) -> None:
    """Rule interface for checking for research groups that have not been modified after a certain amount of months.

    :param ctx: Combined type of a callback and rei struct
    """
    # Only send notifications if inactivity notifications are enabled.
    if not config.enable_inactivity_notification:
        return

    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "inactive research group - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'inactive research group - Checking Research packages for last modification dates')

    zone = user.zone(ctx)
    notify_count = 0
    inactivity_cutoff = datetime.now() - timedelta(weeks=4.35 * config.inactivity_cutoff_months)
    inactivity_cutoff_epoch = int((inactivity_cutoff - datetime(1970, 1, 1)).total_seconds())

    for group_name in group.get_research_groups_list(ctx):
        coll = f'/{zone}/home/{group_name}'

        if not collection.exists(ctx, coll):
            # This is apparently a leftover group, where the collection has already
            # been removed. This is a technical operations issue, rather than a data management
            # issue, so we don't send notification to the data managers about this.
            log.write(ctx, 'inactive research group - Skipping group without collection: ' + group_name)
            continue

        if not collection.has_dataobjects_modified_after(ctx, coll, inactivity_cutoff_epoch, fallback_to_collection_modified=True):
            try:
                datamanagers = folder.get_datamanagers(ctx, coll)
            except ValueError as e:
                log.write(ctx, f"Unable to send inactive group notifications for <{coll}>: cannot get data managers: {str(e)}")
                datamanagers = []

            if len(datamanagers) > 0:
                notify_count += 1
                # Send notifications to datamanager(s).
                message = f"Group '{group_name}' has been inactive for more than {config.inactivity_cutoff_months} months"

                for datamanager in datamanagers:
                    datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
                    actor = 'system'
                    set(ctx, actor, datamanager_name, coll, message)
                log.write(ctx, f'inactive research group - Notifications set for group {group_name} having been inactive since at least {config.inactivity_cutoff_months}. <{coll}>')

    log.write(ctx, f'inactive research group - Finished checking research groups for inactivity | notified: {notify_count}')


@rule.make()
def rule_process_data_access_token_expiry(ctx: rule.Context) -> None:
    """Rule interface for checking for data access tokens that are expiring soon.

    :param ctx: Combined type of a callback and rei struct
    """
    # Only send notifications if expiration notifications are enabled.
    if config.token_expiration_notification == 0:
        return

    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "data access token - Insufficient permissions - should only be called by rodsadmin")
        return

    log.write(ctx, 'data access token - Checking for expiring data access tokens')
    tokens = data_access_token.get_all_tokens(ctx)
    for token in tokens:
        # Calculate token expiration notification date.
        exp_time = datetime.strptime(token['exp_time'], '%Y-%m-%d %H:%M:%S.%f')
        date_exp_time = exp_time - timedelta(hours=config.token_expiration_notification)
        r = relativedelta.relativedelta(date_exp_time, datetime.now().date())
        total_hours = r.years * 12 * 30 * 24 + r.months * 30 * 24 + r.days * 24 + r.hours

        # Send notification if token expires in less than configured hours.
        if total_hours <= config.token_expiration_notification:
            actor = 'system'
            target = str(user.from_str(ctx, token['user']))
            message = f"Data access password with label <{token['label']}> is expiring"
            set(ctx, actor, target, "/user/data_access", message)
            log.write(ctx, f"data access token - Notification set for expiring data access token from user <{token['user']}>")
    log.write(ctx, 'data access token - Finished checking for expiring data access tokens')
