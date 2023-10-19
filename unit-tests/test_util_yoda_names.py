# -*- coding: utf-8 -*-
"""Unit tests for the yoda_names utils functions"""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from yoda_names import _is_internal_user, is_email_username, is_valid_category, is_valid_groupname, is_valid_subcategory


class UtilYodaNamesTest(TestCase):

    def test_is_valid_category(self):
        self.assertEquals(is_valid_category(""), False)
        self.assertEquals(is_valid_category("foo"), True)
        self.assertEquals(is_valid_category("foo123"), True)
        self.assertEquals(is_valid_category("foo-bar"), True)
        self.assertEquals(is_valid_category("foo_bar"), True)

    def test_is_valid_subcategory(self):
        self.assertEquals(is_valid_subcategory(""), False)
        self.assertEquals(is_valid_subcategory("foo"), True)
        self.assertEquals(is_valid_subcategory("foo123"), True)
        self.assertEquals(is_valid_subcategory("foo-bar"), True)
        self.assertEquals(is_valid_subcategory("foo_bar"), True)

    def test_is_valid_groupname(self):
        self.assertEquals(is_valid_groupname(""), False)
        self.assertEquals(is_valid_groupname("foo"), True)
        self.assertEquals(is_valid_groupname("foo123"), True)
        self.assertEquals(is_valid_groupname("foo-bar"), True)
        self.assertEquals(is_valid_groupname("foo_bar"), False)

    def test_is_email_username(self):
        self.assertEquals(is_email_username("peter"), False)
        self.assertEquals(is_email_username("peter@uu.nl"), True)

    def test_is_internal_user(self):
        self.assertEquals(_is_internal_user("peter", ["uu.nl"]), True)
        self.assertEquals(_is_internal_user("peter@uu.nl", ["uu.nl"]), True)
        self.assertEquals(_is_internal_user("peter@vu.nl", ["uu.nl"]), False)
        self.assertEquals(_is_internal_user("peter@buu.nl", ["uu.nl"]), False)
        self.assertEquals(_is_internal_user("peter@uu.nl", ["buu.nl"]), False)
        self.assertEquals(_is_internal_user("peter@uu.nl", ["*.uu.nl"]), True)
        self.assertEquals(_is_internal_user("peter@vu.nl", ["*.uu.nl"]), False)
        self.assertEquals(_is_internal_user("peter@buu.nl", ["*.uu.nl"]), False)
        self.assertEquals(_is_internal_user("peter@cs.uu.nl", ["*.uu.nl"]), True)
        self.assertEquals(_is_internal_user("peter@ai.cs.uu.nl", ["*.cs.uu.nl"]), True)
