"""Unit tests for the util.api module"""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from api import _check_type


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
