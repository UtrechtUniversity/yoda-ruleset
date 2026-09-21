"""Logging facilities."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import inspect

import rule
from config import config


def write(ctx: rule.Context, message: str, write_stdout: bool = False, print_module: bool = True) -> None:
    """Write a message to the log or stdout.
    Includes client name and originating module if writing to log.

    :param ctx:          Combined type of a callback and rei struct
    :param message:      Message to write to log
    :param write_stdout: Whether to write to stdout (used for a few of our scripts)
    :param print_module: Whether to print the calling module in the message (true by default)
    """
    if print_module:
        stack = inspect.stack()[1]
        module = inspect.getmodule(stack[0])
        message_to_print = f"[{module.__name__.replace('rules_uu.', '')}] {message}"
    else:
        message_to_print = message

    if write_stdout:
        ctx.writeLine("stdout", message_to_print)
    else:
        ctx.writeString("serverLog", message_to_print)


def debug(ctx: rule.Context, message: str) -> None:
    """"Write a message to the log, if in a development environment.

    :param ctx:     Combined type of a callback and rei struct
    :param message: Message to write to log
    """
    if config.environment == 'development':
        ctx.writeString("serverLog", f'DEBUG: {message}')
