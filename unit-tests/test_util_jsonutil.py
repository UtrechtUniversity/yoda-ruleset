"""Unit tests for the jsonutil utils module"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.append('../util')

# The 'avu' and 'msi' modules (imported by jsonutil) depend on iRODS-provided
# modules that are not available when running the unit tests. Stub them out
# before importing jsonutil so it can be imported here.
for _irods_module in ('genquery', 'session_vars', 'irods_types'):
    sys.modules.setdefault(_irods_module, MagicMock())

from jsonutil import dump, fast_dump, fast_parse, parse, ParseError  # noqa: E402


class UtilJsonutilTest(TestCase):

    def test_parse(self):
        output = parse('{}')
        self.assertEqual(output, {})
        output = parse('{"key": "value"}')
        self.assertEqual(output, {"key": "value"})
        output = parse('{"str": "text", "int": 42, "float": 1.5, "bool": true, "null": null}')
        self.assertEqual(output, {"str": "text", "int": 42, "float": 1.5, "bool": True, "null": None})
        output = parse('{"outer": {"inner": ["a", "b"]}}')
        self.assertEqual(output, {"outer": {"inner": ["a", "b"]}})
        output = parse('{"text": "éàü"}')
        self.assertEqual(output, {"text": "éàü"})

    def test_parse_returns_ordered_dict(self):
        output = parse('{"z": 1, "a": 2, "m": 3}')
        self.assertIsInstance(output, OrderedDict)
        self.assertEqual(list(output.keys()), ["z", "a", "m"])
        # Nested objects are OrderedDicts as well.
        self.assertIsInstance(parse('{"outer": {"inner": 1}}')["outer"], OrderedDict)

    def test_parse_invalid(self):
        for text in ['', '{invalid}', '{"key": "value"', '{"key": "value",}', 'not valid json']:
            with self.assertRaises(ParseError):
                parse(text)

    def test_fast_parse(self):
        output = fast_parse(b'{}')
        self.assertEqual(output, {})
        output = fast_parse(b'{"key": "value"}')
        self.assertEqual(output, {"key": "value"})
        output = fast_parse(b'{"str": "text", "int": 42, "float": 1.5, "bool": true, "null": null}')
        self.assertEqual(output, {"str": "text", "int": 42, "float": 1.5, "bool": True, "null": None})
        output = fast_parse(b'{"outer": {"inner": ["a", "b"]}}')
        self.assertEqual(output, {"outer": {"inner": ["a", "b"]}})
        output = fast_parse('{"text": "éàü"}'.encode('utf-8'))
        self.assertEqual(output, {"text": "éàü"})

    def test_fast_parse_preserves_key_order(self):
        output = fast_parse(b'{"z": 1, "a": 2, "m": 3}')
        self.assertIsInstance(output, dict)
        self.assertEqual(list(output.keys()), ["z", "a", "m"])

    def test_fast_parse_invalid(self):
        for text in [b'', b'{invalid}', b'{"key": "value"', b'{"key": "value",}', b'not valid json']:
            with self.assertRaises(ParseError):
                fast_parse(text)

    def test_fast_parse_equivalent_to_parse(self):
        text = '{"z": 1, "a": [1, 2, {"b": null}], "m": "é"}'
        self.assertEqual(fast_parse(text.encode('utf-8')), parse(text))

    def test_dump(self):
        # Default output is indented with 4 spaces.
        output = dump({"key": "value"})
        self.assertEqual(output, '{\n    "key": "value"\n}')
        output = dump({})
        self.assertEqual(output, '{}')
        # Options are passed on to json.dumps.
        output = dump({"key": "value"}, indent=None)
        self.assertEqual(output, '{"key": "value"}')
        output = dump({"b": 1, "a": 2}, indent=None, sort_keys=True)
        self.assertEqual(output, '{"a": 2, "b": 1}')

    def test_dump_does_not_escape_unicode(self):
        output = dump({"text": "éàü"}, indent=None)
        self.assertEqual(output, '{"text": "éàü"}')

    def test_dump_roundtrip(self):
        data = {"str": "text", "int": 42, "float": 1.5, "bool": True, "null": None,
                "list": [1, "two", {"three": 3}], "dict": {"nested": {"deep": "value"}},
                "special": 'quote " backslash \\ newline \n tab \t',
                "unicode": "éàü"}
        self.assertEqual(parse(dump(data)), data)

    def test_fast_dump(self):
        # Output is compact, without indentation.
        output = fast_dump({"key": "value"})
        self.assertEqual(output, '{"key":"value"}')
        output = fast_dump({})
        self.assertEqual(output, '{}')
        output = fast_dump({"items": [1, 2, 3]})
        self.assertEqual(output, '{"items":[1,2,3]}')
        output = fast_dump({"str": "text", "int": 42, "float": 1.5, "bool": True, "null": None})
        self.assertEqual(output, '{"str":"text","int":42,"float":1.5,"bool":true,"null":null}')

    def test_fast_dump_returns_string(self):
        output = fast_dump({"key": "value"})
        self.assertIsInstance(output, str)

    def test_fast_dump_ordered_dict(self):
        output = fast_dump(OrderedDict([("z", 1), ("a", 2), ("m", 3)]))
        self.assertEqual(output, '{"z":1,"a":2,"m":3}')

    def test_fast_dump_does_not_escape_unicode(self):
        output = fast_dump({"text": "éàü"})
        self.assertEqual(output, '{"text":"éàü"}')

    def test_fast_dump_roundtrip(self):
        data = {"str": "text", "int": 42, "float": 1.5, "bool": True, "null": None,
                "list": [1, "two", {"three": 3}], "dict": {"nested": {"deep": "value"}},
                "special": 'quote " backslash \\ newline \n tab \t',
                "unicode": "éàü"}
        self.assertEqual(fast_parse(fast_dump(data).encode('utf-8')), data)

    def test_dump_and_fast_dump_equivalent(self):
        data = {"z": 1, "a": [1, 2, {"b": None}], "m": "é"}
        self.assertEqual(parse(fast_dump(data)), parse(dump(data)))
