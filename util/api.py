"""Functions for creating API rules.

For example usage, see make().
"""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64
import inspect
import traceback
import zlib
from collections import OrderedDict
from typing import Any, Callable, get_type_hints

import error
import jsonutil
import log
import rule
from config import config
from measure_coverage import start_coverage, stop_coverage


class Result:
    """API result."""

    def __init__(self, data: dict | None = None, status: str = 'ok', info: str | None = None, debug_info: str | None = None) -> None:
        self.status      = status
        self.status_info = info
        self.data        = data
        self.debug_info  = debug_info

    @staticmethod
    def ok(**xs: int) -> object:
        return Result(**xs)

    def as_dict(self) -> OrderedDict:
        if config.environment == 'development':
            # Emit debug information in dev.
            # This may contain stack traces, exception texts, timing info,
            # etc., which should not be sent to users in production.
            return OrderedDict([('status',      self.status),
                                ('status_info', self.status_info),
                                ('data',        self.data),
                                ('debug_info',  self.debug_info)])
        else:
            return OrderedDict([('status',      self.status),
                                ('status_info', self.status_info),
                                ('data',        self.data)])

    def __bool__(self) -> bool:
        return self.status == 'ok'
    __nonzero__ = __bool__


class Error(Result, error.UUError):
    """Error with descriptive (user-readable) message.

    Returned/raised by API functions to produce informative error output.
    """
    def __init__(self, name: str, info: str, debug_info: str | None = None, data: str | None = None) -> None:
        self.name = name
        self.info = info
        self.debug_info = debug_info

        Result.__init__(self, data, 'error_' + name, info, debug_info)
        error.UUError.__init__(self, 'error_' + name)

    def __str__(self) -> str:
        return f"{self.name}: {self.info}"


def _check_type(value: Any, expected_type: Any) -> bool:
    """Check if a value matches the expected type.

    :param value:         The value to validate
    :param expected_type: The expected type hint to validate against

    :returns: True if the value matches the expected type. False if the value
              does not match.
    """
    if expected_type in (int, str, float, bool, list, dict):
        return isinstance(value, expected_type)

    return False


def _api(f: Callable) -> Callable:
    """Turn a Python function into a basic API function.

    By itself, this wrapper is not very useful, as the resulting function is
    not callable by rules. See make() below for a method to turn the
    result into one or two rules, with different calling conventions.

    api() creates a function that takes a JSON string as an argument,
    and translates it to function arguments for `f`. The JSON input is
    automatically validated for required/optional arguments, based on f()'s
    signature. Basic type checking is also performed based on f()'s type hints.

    f()'s returned value may be of any JSON-encodable type, and will be stored
    in the 'data' field of the returned JSON. If f() returns or raises an
    error, the 'status' and 'status_info' fields are populated (non-null)
    instead.

    In development environments, the result may contain a 'debug_info' property
    with additional information on errors, or timing information.

    :param f: Python function to turn into a API function

    :returns: Wrapper function to turn a Python function into a basic API function
    """
    # Determine required and optional argument names from the function signature.
    full_argspec = inspect.getfullargspec(f)
    a_pos = full_argspec.args
    a_kw = full_argspec.varkw
    a_defaults = full_argspec.defaults

    a_pos = a_pos[1:]  # ignore callback/context param.

    required = set(a_pos if a_defaults is None else a_pos[:-len(a_defaults)])
    optional = set([] if a_defaults is None else a_pos[-len(a_defaults):])

    # If the function accepts **kwargs, we do not forbid extra arguments.
    allow_extra = a_kw is not None

    # Extract type hints for type checking
    type_hints = get_type_hints(f) if hasattr(f, '__annotations__') else {}

    def wrapper(ctx: rule.Context, inp: str) -> dict:
        """A function that receives a JSON string and calls a wrapped function with unpacked arguments.

        :param ctx: Combined type of a callback and rei struct
        :param inp: JSON string

        :raises ParseError: API rule called with invalid JSON argument
        :raises result: API rule returned error

        :returns: Result of the JSON API call
        """
        # Result shorthands.
        def error_internal(debug_info: str | None = None) -> Error:
            return Error('internal', 'An internal error occurred', debug_info=debug_info)

        def bad_request(debug_info: str | None = None) -> Error:
            return Error('badrequest', 'An internal error occurred', debug_info=debug_info)

        # Input is base64 encoded and compressed to reduce size (max rule length in iRODS is 20KB)
        # Validate input string: is it a valid JSON object?
        try:
            base64_decoded = base64.b64decode(inp)
            decompressed_data = zlib.decompress(base64_decoded)
            data = jsonutil.parse(decompressed_data)
            if type(data) is not OrderedDict:
                raise jsonutil.ParseError('Argument is not a JSON object')
        except base64.binascii.Error:
            log.write(ctx, f"Error: API rule <{f.__name__}> input base64 decode error", print_module=False)
            return bad_request('API input base64 decode error').as_dict()
        except zlib.error:
            log.write(ctx, f"Error: API rule <{f.__name__}> input zlib decompression error", print_module=False)
            return bad_request('API input zlib decompression error').as_dict()
        except jsonutil.ParseError as e:
            log.write(ctx, f"Error: API rule <{f.__name__}> called with invalid JSON argument", print_module=False)
            return bad_request(f"JSON parse error: {e}").as_dict()

        # Check that required arguments are present.
        for param in required:
            if param not in data:
                log.write(ctx, f"Error: API rule <{f.__name__}> called with missing <{param}> argument",
                          print_module=False)
                return bad_request(f"Missing argument: {param} (required: [{', '.join(required)}]  optional: [{', '.join(optional)}])").as_dict()

        # Forbid arguments that are not in the function signature.
        if not allow_extra:
            for param in data:
                if param not in required | optional:
                    log.write(ctx, f"Error: API rule <{f.__name__}> called with unrecognized <{param}> argument",
                              print_module=False)
                    return bad_request(f"Unrecognized argument: {param} (required: [{', '.join(required)}]  optional: [{', '.join(optional)}])").as_dict()

        # Type check arguments based on function annotations.
        for param, arg_value in data.items():
            if param in type_hints:
                expected_type = type_hints[param]
                if not _check_type(arg_value, expected_type):
                    log.write(ctx, f"Error: API rule <{f.__name__}> argument <{param}> has invalid type: expected {expected_type}, got {type(arg_value).__name__}",
                              print_module=False)
                    return bad_request(f"Invalid type for argument {param}: expected {expected_type}, got {type(arg_value).__name__}").as_dict()

        # Try to run the function with the supplied arguments,
        # catching any error it throws.
        try:
            if config.measure_coverage:
                cov = start_coverage()

            # Time the request.
            import time
            t = time.time()
            result = f(ctx, **data)
            t = time.time() - t

            log.debug(ctx, f"{int(t * 1000):4d}ms {f.__name__}")

            if config.measure_coverage:
                stop_coverage(cov)

            if type(result) is Error:
                raise result  # Allow api.Errors to be either raised or returned.

            elif not isinstance(result, Result):
                # No error / explicit status info implies 'OK' status.
                result = Result(result, debug_info={'time': t})

            return result.as_dict()
        except Error as e:
            # A proper caught error with name and message.
            if e.debug_info is None:
                log.write(ctx, f"Error: API rule <{f.__name__}> failed with error <{e}>", print_module=False)
            else:
                log.write(ctx,
                          f"Error: API rule <{f.__name__}> failed with error <{e}> (debug info follows below this line)\n{e.debug_info}",
                          print_module=False)
            return e.as_dict()
        except Exception:
            # An uncaught error. Log a trace to aid debugging.
            log.write(ctx,
                      f"Error: API rule <{f.__name__}> failed with uncaught error (trace follows below this line)\n{traceback.format_exc()}",
                      print_module=False)
            return error_internal(traceback.format_exc()).as_dict()

    return wrapper


def make() -> Callable:
    """Create API functions callable as iRODS rules.

    This translate between a Python calling convention and the iRODS rule
    calling convention.

    An iRODS rule is created that receives a JSON string and prints the
    result of f, JSON-encoded to stdout. If an error occurs, the output JSON
    will contain "error" and "error_message" items.

    Synopsis:

        __all__ = ['api_ping']

        @api.make()
        def api_ping(ctx, foo):
            if foo != 42:
                return api.Error('not_allowed', 'Ping is not allowed')
            log.write(ctx, 'ping received')
            return foo

        # this returns {"status": "ok", "status_info": null, "data": 42}
        # when called as api_ping {"foo": 42}

    :returns: API function callable as iRODS rules
    """
    def deco(f: Callable) -> Callable:
        # The "base" API function, that does handling of arguments and errors.
        base = _api(f)

        # The JSON-in, JSON-out rule.
        return rule.make(inputs=[0], outputs=[],
                         transform=jsonutil.dump, handler=rule.Output.STDOUT)(base)

    return deco
