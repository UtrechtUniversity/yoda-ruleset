# -*- coding: utf-8 -*-
"""Utilities for creating PEP rules."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import rule
import log
from error import *

import user
import api

class Permitted(object):
    """Policy function result, indicates ALLOWED action.

    Evaluates to True in boolean context.
    """
    def __str__(self):
        return 'Action permitted'

    def __bool__(self):
        return True
    __nonzero__ = __bool__


class NotPermitted(object):
    """Policy function result, indicates DISALLOWED action.

    Evaluates to False in boolean context.
    """
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return 'Action not permitted: ' + self.reason

    def __bool__(self):
        return False
    __nonzero__ = __bool__


# Shorthands, including fail/succeed terminology for results that
# do not have anything to do with authorization.
deny  = fail    = NotPermitted
allow = succeed =    Permitted


def make_pep():
    """Turn a function into a PEP rule.

    The function must return policy.(Not)Permitted (or .fail()/.succeed()) as a result.
    Any other return type will result in the PEP failing.
    """
    def deco(f):
        @rule.make()
        def r(ctx, *args):
            try:
                result = f(ctx, *args)
            except api.Error as e:
                log._write(ctx, '{} failed/denied due to unhandled API error: {}'.format(f.__name__, str(e)))
                raise
            except Exception as e:
                log._write(ctx, '{} failed/denied due to unhandled internal error: {}'.format(f.__name__, str(e)))
                raise

            if isinstance(result, Permitted):
                return  # succeed the rule (msi "succeed" has no effect here)
            elif isinstance(result, NotPermitted):
                log._write(ctx, '{} denied: {}'.format(f.__name__, str(result)))
                ctx.msiOprDisallowed()
                assert False  # Just in case.

            # We need an unambiguous YES from the policy function.
            # Default to disallowed.
            log._write(ctx, '{} denied: ambiguous policy result (internal error): {}'
                            .format(f.__name__, str(result)))
            ctx.msiOprDisallowed()
            assert False
        return r
    return deco
