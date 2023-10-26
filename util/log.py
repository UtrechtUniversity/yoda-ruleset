# -*- coding: utf-8 -*-
"""Logging facilities."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import inspect
import sys

import rule
from config import config

if 'unittest' not in sys.modules.keys():
    # We don't import the user functions when running unit tests, because then we'll have
    # to deal with their dependencies. When running unit tests we should use a "None" ctx
    # or some mocked object.
    import user


def write(ctx, text):
    """Write a message to the log, including client name and originating rule/API name."""
    caller = inspect.stack()[1][3]
    _write(ctx, '{}: {}'.format(caller, text))


def _write(ctx, text):
    """Write a message to the log, including the client name (intended for internal use)."""
    if type(ctx) is rule.Context:
        ctx.writeLine('serverLog', '{{{}#{}}} {}'.format(*list(user.user_and_zone(ctx)) + [text]))
    else:
        ctx.writeLine('serverLog', text)


def debug(ctx, text):
    """Write a log message if in a development environment."""
    if config.environment == 'development':
        write(ctx, 'DEBUG: {}'.format(text))


def _debug(ctx, text):
    """Write a log message if in a development environment."""
    if config.environment == 'development':
        _write(ctx, 'DEBUG: {}'.format(text))
