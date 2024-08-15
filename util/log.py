# -*- coding: utf-8 -*-
"""Logging facilities."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import inspect
import sys

import rule
from config import config

if 'unittest' not in sys.modules:
    # We don't import the user functions when running unit tests, because then we'll have
    # to deal with their dependencies. When running unit tests we should use a "None" ctx
    # or some mocked object.
    import user


def write(ctx, message):
    """Write a message to the log, including client name and originating module.

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    stack = inspect.stack()[1]
    module = inspect.getmodule(stack[0])
    _write(ctx, '[{}] {}'.format(module.__name__.replace("rules_uu.", ""), message))


def _write(ctx, message):
    """Write a message to the log, including the client name (intended for internal use).

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    if type(ctx) is rule.Context:
        ctx.writeLine('serverLog', '{{{}#{}}} {}'.format(*list(user.user_and_zone(ctx)) + [message]))
    else:
        ctx.writeLine('serverLog', message)


def debug(ctx, message):
    """"Write a message to the log, if in a development environment.

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    if config.environment == 'development':
        _write(ctx, 'DEBUG: {}'.format(message))
