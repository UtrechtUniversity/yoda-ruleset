# -*- coding: utf-8 -*-
"""Rules for sending e-mails."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import email
import re
import smtplib
from email.mime.text import MIMEText

import settings
from util import *

__all__ = ['rule_mail_notification_report',
           'rule_mail_test']


def send(ctx, to, actor, subject, body, cc=None):
    """Send an e-mail with specified recipient, subject and body.

    The originating address and mail server credentials are taken from the
    ruleset configuration file.

    :param ctx:     Combined type of a callback and rei struct
    :param to:      Recipient of the mail
    :param actor:   Actor of the mail
    :param subject: Subject of mail
    :param body:    Body of mail
    :param cc:      Comma-separated list of CC recipient(s) of email (optional)

    :returns: API status
    """
    if not config.notifications_enabled:
        log.write(ctx, '[EMAIL] Notifications are disabled')
        return

    if '@' not in to:
        log.write(ctx, '[EMAIL] Ignoring invalid destination <{}>'.format(to))
        return  # Silently ignore obviously invalid destinations (mimic old behavior).

    if settings.load(ctx, 'mail_notifications', username=to) == "OFF":
        log.write(ctx, '[EMAIL] User <{}> disabled mail notifications'.format(to))
        return

    log.write(ctx, '[EMAIL] Sending mail for <{}> to <{}>, subject <{}>'.format(actor, to, subject))

    cfg = {k: getattr(config, v)
           for k, v in [('from',      'notifications_sender_email'),
                        ('from_name', 'notifications_sender_name'),
                        ('reply_to',  'notifications_reply_to'),
                        ('server',    'smtp_server'),
                        ('username',  'smtp_username'),
                        ('password',  'smtp_password')]}

    try:
        # e.g. 'smtps://smtp.gmail.com:465' for SMTP over TLS, or
        # 'smtp://smtp.gmail.com:587' for STARTTLS on the mail submission port.
        proto, host, port = re.search(r'^(smtps?)://([^:]+)(?::(\d+))?$', cfg['server']).groups()

        # Default to port 465 for SMTP over TLS, and 587 for standard mail
        # submission with STARTTLS.
        port = int(port or (465 if proto == 'smtps' else 587))

    except Exception as e:
        log.write(ctx, '[EMAIL] Configuration error: ' + str(e))
        return api.Error('internal', 'Mail configuration error')

    try:
        smtp = (smtplib.SMTP_SSL if proto == 'smtps' else smtplib.SMTP)(host, port)

        if proto != 'smtps':
            # Enforce TLS.
            smtp.starttls()

    except Exception as e:
        log.write(ctx, '[EMAIL] Could not connect to mail server at {}://{}:{}: {}'.format(proto, host, port, e))
        return api.Error('internal', 'Mail configuration error')

    try:
        smtp.login(cfg['username'], cfg['password'])

    except Exception:
        log.write(ctx, '[EMAIL] Could not login to mail server with configured credentials')
        return api.Error('internal', 'Mail configuration error')

    fmt_addr = '{} <{}>'.format

    msg = MIMEText(body)
    msg['Reply-To'] = cfg['reply_to']
    msg['Date'] = email.utils.formatdate()
    msg['From'] = fmt_addr(cfg['from_name'], cfg['from'])
    msg['To'] = to
    msg['Subject'] = subject

    if cc is not None:
        msg['Cc'] = cc

    try:
        if cc is not None:
            smtp.sendmail(cfg['from'], [to] + cc.split(','), msg.as_string())
        else:
            smtp.sendmail(cfg['from'], [to], msg.as_string())
    except Exception as e:
        log.write(ctx, '[EMAIL] Could not send mail: {}'.format(e))
        return api.Error('internal', 'Mail configuration error')

    try:
        smtp.quit()
    except Exception:
        pass


def _wrapper(ctx, to, actor, subject, body):
    """Send mail, returns status/statusinfo in rule-language style."""
    x = send(ctx, to, actor, subject, body)

    if type(x) is api.Error:
        return '1', x.info
    return '0', ''


def notification(ctx, to, actor, message):
    return _wrapper(ctx,
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


@rule.make(inputs=range(1), outputs=range(1, 3))
def rule_mail_test(ctx, to):
    if not user.is_admin(ctx):
        return api.Error('not_allowed', 'Only rodsadmin can send test mail')

    return _wrapper(ctx,
                    to=to,
                    actor='None',
                    subject='[Yoda] Test mail',
                    body="""
Congratulations, you have sent a test mail from your Yoda system.

Best regards,
Yoda system
""")
