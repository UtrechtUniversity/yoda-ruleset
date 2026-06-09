"""Unit tests for the yoda_names utils functions"""

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from datetime import datetime, timedelta
from unittest import TestCase

sys.path.append('../util')

from yoda_names import _is_internal_user, is_email_username, is_valid_category, is_valid_expiration_date, is_valid_groupname, is_valid_schema_id, is_valid_subcategory


class UtilYodaNamesTest(TestCase):

    def test_is_valid_category(self):
        self.assertEqual(is_valid_category(""), False)
        self.assertEqual(is_valid_category("lowercaseletters"), True)
        self.assertEqual(is_valid_category("lowercase-withdash"), True)
        self.assertEqual(is_valid_category("lowercase.withdot"), False)
        self.assertEqual(is_valid_category("lowercase,withcomma"), False)
        self.assertEqual(is_valid_category("lowercase_withunderscore"), False)
        self.assertEqual(is_valid_category("lowercase(withparentheses)"), False)
        self.assertEqual(is_valid_category("lowercase with spaces"), False)
        self.assertEqual(is_valid_category("lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_category("lowercase-endswithdash-"), False)
        self.assertEqual(is_valid_category("-lowercase-beginswithdash"), False)
        self.assertEqual(is_valid_category("MiXeDcASe"), False)
        self.assertEqual(is_valid_category("toolong" + 2700 * "a"), False)

    def test_is_valid_subcategory(self):
        self.assertEqual(is_valid_subcategory(""), False)
        self.assertEqual(is_valid_subcategory("lowercaseletters"), True)
        self.assertEqual(is_valid_subcategory("lowercase-withdash"), True)
        self.assertEqual(is_valid_subcategory("lowercase.withdot"), True)
        self.assertEqual(is_valid_subcategory("lowercase,withcomma"), True)
        self.assertEqual(is_valid_subcategory("lowercase_withunderscore"), True)
        self.assertEqual(is_valid_subcategory("lowercase(withparentheses)"), True)
        self.assertEqual(is_valid_subcategory("lowercase with spaces"), True)
        self.assertEqual(is_valid_subcategory("lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_subcategory("lowercase-endswithdash-"), True)
        self.assertEqual(is_valid_subcategory("-lowercase-beginswithdash"), True)
        self.assertEqual(is_valid_subcategory("MiXeDcASe"), True)
        self.assertEqual(is_valid_subcategory("toolong" + 2700 * "a"), False)

    def test_is_valid_groupname(self):
        self.assertEqual(is_valid_groupname(""), False)
        self.assertEqual(is_valid_groupname("research-lowercaseletters"), True)
        self.assertEqual(is_valid_groupname("research-lowercase-withdash"), True)
        self.assertEqual(is_valid_groupname("research-lowercase.withdot"), False)
        self.assertEqual(is_valid_groupname("research-lowercase,withcomma"), False)
        self.assertEqual(is_valid_groupname("research-lowercase_withunderscore"), False)
        self.assertEqual(is_valid_groupname("research-lowercase(withparentheses)"), False)
        self.assertEqual(is_valid_groupname("research-lowercase with spaces"), False)
        self.assertEqual(is_valid_groupname("research-lowercase-withnumbersanddash-123"), True)
        self.assertEqual(is_valid_groupname("research-lowercase-endswithdash-"), False)
        self.assertEqual(is_valid_groupname("-lowercase-beginswithdash"), False)
        self.assertEqual(is_valid_groupname("research-MiXeDcASe"), False)
        self.assertEqual(is_valid_groupname("toolong" + 57 * "a"), False)

    def test_is_email_username(self):
        self.assertEqual(is_email_username("peter"), False)
        self.assertEqual(is_email_username("peter@uu.nl"), True)

    def test_is_internal_user(self):
        self.assertEqual(_is_internal_user("peter", ["uu.nl"]), True)
        self.assertEqual(_is_internal_user("peter@uu.nl", ["uu.nl"]), True)
        self.assertEqual(_is_internal_user("peter@vu.nl", ["uu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@buu.nl", ["uu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@uu.nl", ["buu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@uu.nl", ["*.uu.nl"]), True)
        self.assertEqual(_is_internal_user("peter@vu.nl", ["*.uu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@buu.nl", ["*.uu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@cs.uu.nl", ["*.uu.nl"]), True)
        self.assertEqual(_is_internal_user("peter@ai.cs.uu.nl", ["*.cs.uu.nl"]), True)
        self.assertEqual(_is_internal_user("peter@ai.hum.uu.nl", ["*.cs.uu.nl"]), False)
        self.assertEqual(_is_internal_user("peter@uu.nl", ["*"]), True)
        self.assertEqual(_is_internal_user("peter@vu.nl", ["*"]), True)

    def test_is_valid_expiration_date(self):
        # Empty and "." represent "no expiration date" and are accepted.
        self.assertEqual(is_valid_expiration_date(""), True)
        self.assertEqual(is_valid_expiration_date("."), True)
        # A correctly formatted date in the future is accepted.
        future = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        self.assertEqual(is_valid_expiration_date(future), True)
        # Today and past dates are rejected (expiration must be strictly in the future).
        self.assertEqual(is_valid_expiration_date(datetime.now().strftime('%Y-%m-%d')), False)
        past = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.assertEqual(is_valid_expiration_date(past), False)
        # Wrong format or impossible dates are rejected.
        self.assertEqual(is_valid_expiration_date("2999-13-01"), False)
        self.assertEqual(is_valid_expiration_date("2999-02-30"), False)
        self.assertEqual(is_valid_expiration_date("2999-1-1"), False)
        self.assertEqual(is_valid_expiration_date("01-01-2999"), False)
        self.assertEqual(is_valid_expiration_date("not-a-date"), False)

    def test_is_valid_schema_id(self):
        # Empty string is accepted (represents "no schema id").
        self.assertEqual(is_valid_schema_id(""), True)
        self.assertEqual(is_valid_schema_id("default-0"), True)
        self.assertEqual(is_valid_schema_id("default-1"), True)
        self.assertEqual(is_valid_schema_id("default-01"), True)
        self.assertEqual(is_valid_schema_id("dag-0"), True)
        self.assertEqual(is_valid_schema_id("noversion"), False)
        self.assertEqual(is_valid_schema_id("default-1a"), False)
        self.assertEqual(is_valid_schema_id("default-"), False)
        self.assertEqual(is_valid_schema_id("-0"), False)
        self.assertEqual(is_valid_schema_id("under_score-1"), False)
        self.assertEqual(is_valid_schema_id("with space-1"), False)
        self.assertEqual(is_valid_schema_id("dot.name-1"), False)
