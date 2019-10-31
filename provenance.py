# -*- coding: utf-8 -*-
"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['rule_uu_provenance_log_action']


def rule_uu_provenance_log_action(rule_args, callback, rei):
    """Frontend function to add action log record to specific folder.

       :param actor: rodsaccount coming from yoda frontend
       :param folder: folder the logging is linked to
       :param action: the text that is logged

       :returns: string -- JSON object with status info
    """
    actor, folder, action = rule_args[0:3]

    # actor to be reformatted to yoda user - name#zone
    this_actor = actor.split(':')[0].replace('.', '#')

    status = 'Success'
    statusInfo = ''

    def report(x):
        # callback.writeString("serverLog", x)
        callback.writeString("stdout", x)

    callback.iiAddActionLogRecord(this_actor, folder, action)

    report(jsonutil.dump({'status':     status,
                       'statusInfo': statusInfo}))
