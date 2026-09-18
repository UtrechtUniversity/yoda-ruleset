"""Unit tests for the schema utils module"""

__copyright__ = 'Copyright (c) 2025-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from schema_utils import is_unsupported_schema, is_valid_blocks_list, is_valid_schema_identifier


class SchemaUtilsTest(TestCase):

    def test_is_unsupported_schema(self):
        # Known unsupported schema
        self.assertEqual(is_unsupported_schema("https://yoda.uu.nl/schemas/default-0/metadata.json"), True)
        # No schema is unsupported as well
        self.assertEqual(is_unsupported_schema(None), True)
        # Schemas that we don't know are not marked as (known to be) unsupported
        self.assertEqual(is_unsupported_schema("https://wedontknow.com/this-schema/metadata.json"), False)

    def test_is_valid_schema_identifier_valid(self):
        """Test valid schema identifiers."""
        self.assertTrue(is_valid_schema_identifier("customSchema123"))
        self.assertTrue(is_valid_schema_identifier("abc123XYZ"))
        self.assertTrue(is_valid_schema_identifier("a" * 50))        # Max length

    def test_is_valid_schema_identifier_invalid(self):
        self.assertFalse(is_valid_schema_identifier(""))             # Empty string
        self.assertFalse(is_valid_schema_identifier(None))           # None
        self.assertFalse(is_valid_schema_identifier(123))            # Not a string
        self.assertFalse(is_valid_schema_identifier("a" * 51))       # Exceeds max length
        self.assertFalse(is_valid_schema_identifier("schema-name"))  # Contains hyphen
        self.assertFalse(is_valid_schema_identifier("schema name"))  # Contains space
        self.assertFalse(is_valid_schema_identifier("schema_name"))  # Contains underscore
        self.assertFalse(is_valid_schema_identifier("schema@name"))  # Contains special char

    def test_is_valid_blocks_list_valid(self):
        self.assertTrue(is_valid_blocks_list(["block1", "block2"], ["block1"]))
        self.assertTrue(is_valid_blocks_list(["block1", "block2", "block3"], ["block1", "block2"]))
        self.assertTrue(is_valid_blocks_list(["a", "b", "c", "d", "e"], ["a", "b", "c", "d", "e"]))

    def test_is_valid_blocks_list_invalid_format(self):
        self.assertFalse(is_valid_blocks_list(["block1"], []))        # Empty blocks list
        self.assertFalse(is_valid_blocks_list(["block1"], None))      # None instead of list
        self.assertFalse(is_valid_blocks_list(["block1"], "block1"))  # String instead of list
        self.assertFalse(is_valid_blocks_list(["block1"], 123))       # Integer instead of list

    def test_is_valid_blocks_list_size_limit(self):
        available = [f"block{i}" for i in range(15)]
        self.assertFalse(is_valid_blocks_list(available, available))  # 15 blocks exceeds max of 10

    def test_is_valid_blocks_list_duplicates(self):
        self.assertFalse(is_valid_blocks_list(["block1", "block2"], ["block1", "block1"]))
        self.assertFalse(is_valid_blocks_list(["a", "b", "c"], ["a", "b", "a"]))

    def test_is_valid_blocks_list_unavailable(self):
        self.assertFalse(is_valid_blocks_list(["block1", "block2"], ["block1", "block3"]))
        self.assertFalse(is_valid_blocks_list(["a"], ["b"]))

    def test_is_valid_blocks_list_invalid_block_entries(self):
        self.assertFalse(is_valid_blocks_list(["block1"], ["block1", ""]))     # Empty string block
        self.assertFalse(is_valid_blocks_list(["block1"], ["block1", None]))   # None block
        self.assertFalse(is_valid_blocks_list(["block1"], ["block1", 123]))    # Integer block
        self.assertFalse(is_valid_blocks_list(["block1"], ["block1", "   "]))  # Whitespace-only block

    def test_is_valid_blocks_list_invalid_available_blocks(self):
        self.assertFalse(is_valid_blocks_list(None, ["block1"]))               # None available_blocks
        self.assertFalse(is_valid_blocks_list("block1", ["block1"]))           # String instead of list
