# -*- coding: utf-8 -*-
"""Unit tests for the misc utils module"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
import time
from collections import OrderedDict
from unittest import TestCase

sys.path.append('../util')

from misc import human_readable_size, last_run_time_acceptable, remove_empty_objects


class UtilMiscTest(TestCase):

    def test_last_run_time_acceptable(self):
        """Test the last run time for copy to vault"""
        # No last run time (job hasn't been tried before)
        found = False
        last_run = 1
        self.assertEqual(last_run_time_acceptable(found, last_run, 300), True)

        # Last run time greater than the backoff, so can run
        now = int(time.time())
        found = True
        copy_backoff_time = 300
        last_run = now - copy_backoff_time - 1
        self.assertEqual(last_run_time_acceptable(found, last_run, copy_backoff_time), True)

        # Last run time more recent than the backoff, so should not run
        found = True
        copy_backoff_time = 300
        last_run = now
        self.assertEqual(last_run_time_acceptable(found, int(time.time()), copy_backoff_time), False)

    def test_human_readable_size(self):
        output = human_readable_size(0)
        self.assertEqual(output, "0 B")
        output = human_readable_size(1024)
        self.assertEqual(output, "1.0 KiB")
        output = human_readable_size(1048576)
        self.assertEqual(output, "1.0 MiB")
        output = human_readable_size(26843550000)
        self.assertEqual(output, "25.0 GiB")
        output = human_readable_size(989560500000000)
        self.assertEqual(output, "900.0 TiB")
        output = human_readable_size(112590000000000000)
        self.assertEqual(output, "100.0 PiB")
        output = human_readable_size(3931462330709348188)
        self.assertEqual(output, "3.41 EiB")

    def test_remove_empty_objects(self):
        d = OrderedDict({"key1": None, "key2": "", "key3": {}, "key4": []})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({}))
        d = OrderedDict({"key1": "value1", "key2": {"key1": None, "key2": "", "key3": {}, "key4": []}})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1"}))
        d = OrderedDict({"key1": "value1", "key2": {"key1": None, "key2": "", "key3": {}, "key4": [], "key5": "value5"}})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1", "key2": {"key5": "value5"}}))
        d = OrderedDict({"key1": "value1", "key2": [{}]})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1"}))
