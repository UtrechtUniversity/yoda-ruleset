# -*- coding: utf-8 -*-
"""Logging facilities."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import inspect

import rule
import user
from config import config


def write(ctx, message):
    """Write a message to the log, including client name and originating module.

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    stack = inspect.stack()[1]
    module = inspect.getmodule(stack[0])
    _write(ctx, u'[{}] {}'.format(module.__name__.replace("rules_uu.", ""), message))


def _write(ctx, message):
    """Write a message to the log, including the client name (intended for internal use).

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    if type(ctx) is rule.Context:
        ctx.writeLine('serverLog', u'{{{}#{}}} {}'.format(*list(user.user_and_zone(ctx)) + [message]))
    else:
        ctx.writeLine('serverLog', message)


def debug(ctx, message):
    """"Write a message to the log, if in a development environment.

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    if config.environment == 'development':
        _write(ctx, 'DEBUG: {}'.format(message))
