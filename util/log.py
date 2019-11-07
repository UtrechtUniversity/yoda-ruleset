# -*- coding: utf-8 -*-
"""Logging facilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import user
import rule
import inspect

def write(ctx, text):
    """Write a message to the log, including client name and originating rule/API name"""
    caller = inspect.stack()[1][3]
    _write(ctx, '{}: {}'.format(caller, text))

def _write(ctx, text):
    """Write a message to the log, including the client name.
    (intended for internal use)
    """
    if type(ctx) is rule.Context:
        ctx.writeLine('serverLog', '{{{}#{}}} {}'.format(*list(user.user_and_zone(ctx)) + [text]))
    else:
        ctx.writeLine('serverLog', text)
