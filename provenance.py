# -*- coding: utf-8 -*-
"""Functions for provenance handling."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


def iiFrontEndAddActionLogRecord(rule_args, callback, rei):
    """Frontend function to add action log record to specific folder.

       Arguments:
       actor  -- rodsaccount coming from yoda frontend
       folder -- folder the logging is linked to
       action -- the text that is logged

       Return:
       string -- JSON object with status info
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
    return
