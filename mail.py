# -*- coding: utf-8 -*-
"""Rules for sending e-mails"""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
import email
from email.mime.text import MIMEText
import smtplib

from util import *

__all__ = ['rule_uu_mail_new_package_published',
           'rule_uu_mail_your_package_published']


def send(ctx, to, actor, subject, body):
    """Sends an e-mail with specified recipient, subject and body.

    The originating address and mail server credentials are taken from the
    ruleset configuration file.
    """
    if not config.notifications_enabled:
        log.write(ctx, '[EMAIL] Notifications are disabled')
        return

    if not user.is_admin(ctx):
        return api.Error('not_allowed', 'Only rodsadmin can send mail')

    if '@' not in to:
        log.write(ctx, '[EMAIL] Ignoring invalid destination <{}>'.format(to))
        return  # Silently ignore obviously invalid destinations (mimic old behavior).

    log.write(ctx, '[EMAIL] Sending mail for <{}> to <{}>, subject <{}>'.format(actor, to, subject))

    cfg = {k: getattr(config, v)
           for k, v in
               [('from',      'notifications_sender_email'),
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

    except Exception as e:
        log.write(ctx, '[EMAIL] Could not login to mail server with configured credentials')
        return api.Error('internal', 'Mail configuration error')

    fmt_addr = '{} <{}>'.format

    msg = MIMEText(body)
    msg['Reply-To'] = cfg['reply_to']
    msg['Date']     = email.utils.formatdate()
    msg['From']     = fmt_addr(cfg['from_name'], cfg['from'])
    msg['To']       = to
    msg['Subject']  = subject

    try:
        smtp.sendmail(cfg['from'], [to], msg.as_string())
    except Exception as e:
        log.write(ctx, '[EMAIL] Could not send mail: {}'.format(e))
        return api.Error('internal', 'Mail configuration error')

    try:
        smtp.quit()
    except Exception as e:
        pass


def _wrapper(ctx, to, actor, subject, body):
    """Sends mail, returns status/statusinfo in rule-language style."""
    x = send(ctx, to, actor, subject, body)

    if type(x) is api.Error:
        return '1', x.info
    return '0', ''


@rule.make(inputs=range(4), outputs=range(4,6))
def rule_uu_mail_new_package_published(ctx, datamanager, actor, title, doi):
    return _wrapper(ctx,
                    to      = datamanager,
                    actor   = actor,
                    subject = '[Yoda] New package is published with DOI: {}'.format(doi),
                    body    =
"""Congratulations, your data has been published.

Title: {}
DOI:   {} (https://doi.org/{})

Best regards,
Yoda system
""".format(title, doi, doi))


@rule.make(inputs=range(4), outputs=range(4,6))
def rule_uu_mail_your_package_published(ctx, researcher, actor, title, doi):
    return _wrapper(ctx,
                    to      = researcher,
                    actor   = actor,
                    subject = '[Yoda] Your package is published with DOI: {}'.format(doi),
                    body    =
"""Congratulations, your data has been published.

Title: {}
DOI:   {} (https://doi.org/{})

Best regards,
Yoda system
""".format(title, doi, doi))
