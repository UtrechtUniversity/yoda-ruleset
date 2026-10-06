"""Unit tests for the util.api module"""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64
import hashlib
import json
import sys
import zlib
from typing import Optional, Union
from unittest import TestCase

sys.path.append('../util')

import jsonutil
from api import (
    _api,
    _check_type,
    api_stage_multipart_request_clear,
    api_stage_multipart_request_run,
    api_stage_multipart_request_submit,
    make,
    MAX_INPUT_SIZE,
    MULTIPART_MAX_TOTAL_SIZE,
)


# --- Test helpers for encoding/decoding API input ---------------------------

def encode_input(data: dict) -> str:
    """Encode a dict of API arguments into the format expected by api._api()'s wrapper."""
    return base64.b64encode(zlib.compress(jsonutil.dump(data).encode('utf-8'))).decode('ascii')


class DummyContext:
    def writeString(self, stream, message):
        pass


class OutputContext:
    """Rule callback that records what a rule writes to stdout."""
    def __init__(self):
        self.stdout = []

    def writeString(self, stream, message):
        if stream == 'stdout':
            self.stdout.append(message)


def call_rule(rule_function, data: dict) -> dict:
    """Call an API rule (as created by api.make()) like iRODS would, and return its parsed output."""
    callback = OutputContext()
    rule_function([encode_input(data)], callback, None)
    return json.loads(callback.stdout[-1])


# An API function to call through multi-part requests. Registered by make(),
# just like the API functions of the ruleset modules.
def api_unit_test_echo(ctx, text: str):
    return text


make()(api_unit_test_echo)


class UtilAPITest(TestCase):

    def test_check_type(self):
        # Simple matches
        self.assertTrue(_check_type(None, type(None)))
        self.assertTrue(_check_type(42, int))
        self.assertTrue(_check_type("banana", str))
        self.assertTrue(_check_type(3.14, float))
        self.assertTrue(_check_type(True, bool))
        self.assertTrue(_check_type([], list))
        self.assertTrue(_check_type({}, dict))

        # Should not match
        self.assertFalse(_check_type("banana", type(None)))
        self.assertFalse(_check_type("banana", int))
        self.assertFalse(_check_type(3, str))
        self.assertFalse(_check_type("banana", float))
        self.assertFalse(_check_type("banana", bool))
        self.assertFalse(_check_type("banana", list))
        self.assertFalse(_check_type("banana", dict))

        # Accepts int as float, because JSON does not differentiate
        # between them
        self.assertTrue(_check_type(42, float))

    def test_check_type_union(self):
        union_type = Union[int, str, None]

        self.assertTrue(_check_type(42, union_type))
        self.assertTrue(_check_type("banana", union_type))
        self.assertTrue(_check_type(None, union_type))
        self.assertFalse(_check_type(3.14, union_type))
        self.assertFalse(_check_type([], union_type))

    def test_check_type_optional(self):
        optional_str = Optional[str]
        self.assertTrue(_check_type("banana", optional_str))
        self.assertTrue(_check_type(None, optional_str))
        self.assertFalse(_check_type(42, optional_str))

    def test_check_type_unsupported_type(self):
        # Any type hint outside of the explicitly-handled set (int, str,
        # float, bool, list, dict, NoneType, unions) is rejected, regardless
        # of value -- e.g. a custom class used as a type hint.
        class Custom:
            pass

        self.assertFalse(_check_type(Custom(), Custom))
        self.assertFalse(_check_type(42, Custom))

    def test_api_wrapper_rejects_wrong_type(self):
        # End-to-end: the API wrapper should reject a call whose JSON
        # argument value does not match the function's type hint.
        def f(ctx, name: str, age: int):
            return {'name': name, 'age': age}

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'name': 'Yoda', 'age': 'old'}))

        self.assertTrue(result['status'].startswith('error_'))
        self.assertIn('Invalid type for argument age', result['status_info'])

    def test_api_wrapper_accepts_correct_type(self):
        def f(ctx, name: str, age: int):
            return {'name': name, 'age': age}

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'name': 'Yoda', 'age': 900}))

        self.assertEqual(result['status'], 'ok')
        self.assertDictEqual(result['data'], {'name': 'Yoda', 'age': 900})

    def test_api_wrapper_accepts_int_for_float_argument(self):
        # JSON has no distinct integer/float types, so a `float`-annotated
        # argument must accept an int value coming from JSON.
        def f(ctx, amount: float):
            return amount

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'amount': 42}))

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data'], 42)

    def test_api_wrapper_accepts_none_for_oldstyle_optional_argument(self):
        def f(ctx, name: Optional[str] = None):
            return name

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'name': None}))

        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['data'])

    def test_api_wrapper_skips_type_check_for_untyped_argument(self):
        # Arguments without a type hint are not type-checked at all.
        def f(ctx, anything):
            return anything

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'anything': {'nested': [1, 2, 3]}}))

        self.assertEqual(result['status'], 'ok')
        self.assertDictEqual(result['data'], {'nested': [1, 2, 3]})

    def test_api_wrapper_reports_missing_required_argument(self):
        def f(ctx, name: str, age: int):
            return {'name': name, 'age': age}

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'name': 'Yoda'}))

        self.assertTrue(result['status'].startswith('error_'))
        self.assertIn('Missing argument: age', result['status_info'])

    def test_api_wrapper_reports_unrecognized_argument(self):
        def f(ctx, name: str):
            return name

        wrapped = _api(f)
        result = wrapped(DummyContext(), encode_input({'name': 'Yoda', 'extra': 1}))

        self.assertTrue(result['status'].startswith('error_'))
        self.assertIn('Unrecognized argument: extra', result['status_info'])

    def test_api_wrapper_invalid_base64(self):
        wrapped = _api(lambda ctx: None)
        result = wrapped(DummyContext(), 'not valid base64!!!')

        self.assertTrue(result['status'].startswith('error_'))

    def test_api_wrapper_invalid_zlib(self):
        wrapped = _api(lambda ctx: None)
        # Valid base64, but not valid zlib-compressed data underneath.
        result = wrapped(DummyContext(), base64.b64encode(b'not zlib data').decode('ascii'))

        self.assertTrue(result['status'].startswith('error_'))

    def test_api_wrapper_invalid_json(self):
        wrapped = _api(lambda ctx: None)
        bad_json = base64.b64encode(zlib.compress(b'not json')).decode('ascii')
        result = wrapped(DummyContext(), bad_json)

        self.assertTrue(result['status'].startswith('error_'))

    def test_api_wrapper_rejects_non_object_json(self):
        # A JSON array (or any non-object) is valid JSON but not a valid
        # set of named arguments.
        wrapped = _api(lambda ctx: None)
        non_object = base64.b64encode(zlib.compress(jsonutil.dump([1, 2, 3]).encode('utf-8'))).decode('ascii')
        result = wrapped(DummyContext(), non_object)

        self.assertTrue(result['status'].startswith('error_'))

    def test_api_wrapper_rejects_input_exceeding_max_size(self):
        # Highly compressible input that would decompress to more than the
        # maximum input size (a "decompression bomb").
        wrapped = _api(lambda ctx, text: None)
        result = wrapped(DummyContext(), encode_input({'text': 'x' * MAX_INPUT_SIZE}))

        self.assertTrue(result['status'].startswith('error_'))

    def run_multipart(self, encoded: str, chunk_size: int, function: str, checksum: str) -> dict:
        """Send encoded API input as a multi-part request, and return the output of the run step."""
        call_rule(api_stage_multipart_request_clear, {})
        for i in range(0, len(encoded), chunk_size):
            submit_result = call_rule(api_stage_multipart_request_submit, {'chunk': encoded[i:i + chunk_size]})
            self.assertEqual(submit_result['status'], 'ok')
        return call_rule(api_stage_multipart_request_run, {'function': function, 'checksum': checksum})

    def test_multipart_request(self):
        params = {'text': 'Yoda ' * 10000}
        checksum = hashlib.shake_256(jsonutil.dump(params).encode('utf-8')).hexdigest(20)

        result = self.run_multipart(encode_input(params), 100, 'unit_test_echo', checksum)

        # Same output as a direct call of the API function.
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data'], params['text'])

    def test_multipart_request_passes_on_api_errors(self):
        # Missing argument: the API function's own error is returned.
        checksum = hashlib.shake_256(jsonutil.dump({}).encode('utf-8')).hexdigest(20)

        result = self.run_multipart(encode_input({}), 10, 'unit_test_echo', checksum)

        self.assertEqual(result['status'], 'error_badrequest')
        self.assertIn('Missing argument: text', result['status_info'])

    def test_multipart_request_incomplete(self):
        params = {'text': 'Yoda ' * 10000}
        checksum = hashlib.shake_256(jsonutil.dump(params).encode('utf-8')).hexdigest(20)
        encoded = encode_input(params)

        # Last part missing.
        result = self.run_multipart(encoded[:-10], 100, 'unit_test_echo', checksum)
        self.assertEqual(result['status'], 'error_multipart_incomplete')

        # Nothing staged (e.g. parts were sent to another agent).
        result = call_rule(api_stage_multipart_request_run, {'function': 'unit_test_echo', 'checksum': checksum})
        self.assertEqual(result['status'], 'error_multipart_incomplete')

    def test_multipart_request_wrong_checksum(self):
        result = self.run_multipart(encode_input({'text': 'Yoda'}), 10, 'unit_test_echo', '0' * 40)

        self.assertEqual(result['status'], 'error_multipart_incomplete')

    def test_multipart_request_unknown_function(self):
        params = {'text': 'Yoda'}
        checksum = hashlib.shake_256(jsonutil.dump(params).encode('utf-8')).hexdigest(20)

        for function in ['does_not_exist', 'stage_multipart_request_run', 'stage_multipart_request_clear']:
            result = self.run_multipart(encode_input(params), 10, function, checksum)
            self.assertEqual(result['status'], 'error_badrequest')
            self.assertIn('Unknown API function', result['status_info'])

    def test_multipart_request_too_large(self):
        call_rule(api_stage_multipart_request_clear, {})
        result = call_rule(api_stage_multipart_request_submit, {'chunk': 'A' * (MULTIPART_MAX_TOTAL_SIZE + 1)})

        self.assertEqual(result['status'], 'error_multipart_too_large')
