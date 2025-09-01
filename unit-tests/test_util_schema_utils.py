"""Unit tests for the schema utils module"""

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from schema_utils import is_unsupported_schema


class SchemaUtilsTest(TestCase):

    def test_is_unsupported_schema(self):
        # Known unsupported schema
        self.assertEqual(is_unsupported_schema("https://yoda.uu.nl/schemas/default-0/metadata.json"), True)
        # No schema is unsupported as well
        self.assertEqual(is_unsupported_schema(None), True)
        # Schemas that we don't know are not marked as (known to be) unsupported
        self.assertEqual(is_unsupported_schema("https://wedontknow.com/this-schema/metadata.json"), False)
