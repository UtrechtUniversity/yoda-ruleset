# -*- coding: utf-8 -*-
"""Unit tests for the misc utils module"""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from misc import human_readable_size


class UtilMiscTest(TestCase):

    def test_dataset_parse_id(self):
        output = human_readable_size(0)
        self.assertEquals(output, "0 B")
        output = human_readable_size(1024)
        self.assertEquals(output, "1.0 KiB")
        output = human_readable_size(1048576)
        self.assertEquals(output, "1.0 MiB")
        output = human_readable_size(26843550000)
        self.assertEquals(output, "25.0 GiB")
        output = human_readable_size(989560500000000)
        self.assertEquals(output, "900.0 TiB")
        output = human_readable_size(112590000000000000)
        self.assertEquals(output, "100.0 PiB")
        output = human_readable_size(3931462330709348188)
        self.assertEquals(output, "3.41 EiB")
