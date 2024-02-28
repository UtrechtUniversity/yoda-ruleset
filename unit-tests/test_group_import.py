# -*- coding: utf-8 -*-

"""Unit tests for the groups functionality
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import io
import sys
from unittest import TestCase

sys.path.append('..')

from groups_import import get_duplicate_columns, parse_data, process_csv_line


class GroupImportTest(TestCase):

    def test_duplicate_columns(self):
        columns = ["category", "subcategory", "groupname", "category"]
        result = get_duplicate_columns(columns)
        self.assertSetEqual(result, set({"category"}))

    def parse_csv_file(self, filename):
        with io.open(filename, "r", encoding='utf-8-sig') as file:
            data = file.read()
        return parse_data('', data)

    def test_fully_filled_csv_line(self):
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_multi_role(self):
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            "member": ["p.member@yoda.dev", "q.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            ["p.member@yoda.dev", "q.member@yoda.dev"],
            ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_with_suffixes(self):
        # Confirm support the old csv header format still (with ":nicknameofuser")
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager:alice": ["m.manager@yoda.dev"],
            "member:bob": ["p.member@yoda.dev"],
            "viewer:eve": ["m.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_fully_filled_csv_line_with_suffixes_multi_role(self):
        # Confirm support the old csv header format still (with ":nicknameofuser")
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager:alice": ["m.manager@yoda.dev"],
            "manager:andy": ["n.manager@yoda.dev"],
            "member:bella": ["p.member@yoda.dev"],
            "member:bob": ["q.member@yoda.dev"],
            "viewer:emma": ["m.viewer@yoda.dev"],
            "viewer:eve": ["n.viewer@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev", "n.manager@yoda.dev"],
            ["p.member@yoda.dev", "q.member@yoda.dev"],
            ["m.viewer@yoda.dev", "n.viewer@yoda.dev"],
            "default-3",
            "2030-01-01",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

    def test_missing_fields(self):
        # No schema id or expiration date
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "",
            "",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

        # schema id, expiration date empty strings (should not give an error)
        d = {
            "category": ["test-automation"],
            "subcategory": ["initial"],
            "groupname": ["groupteama"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["p.member@yoda.dev"],
            "viewer": ["m.viewer@yoda.dev"],
            "schema_id": [""],
            "expiration_date": [""],
        }
        expected = (
            "test-automation",
            "initial",
            "research-groupteama",
            ["m.manager@yoda.dev"],
            ["p.member@yoda.dev"],
            ["m.viewer@yoda.dev"],
            "",
            "",
        )
        result, error_msg = process_csv_line('', d)
        self.assertTupleEqual(expected, result)
        self.assertIsNone(error_msg)

        # Missing subcategory (should give error)
        d = {
            "category": ["test-automation"],
            "groupname": ["groupteama2"],
            "manager": ["m.manager@yoda.dev"],
            "member": ["m.member@yoda.dev", "m.member2@yoda.dev"],
            "expiration_date": ["2030-01-01"],
            "schema_id": ["default-3"],
        }
        result, error_msg = process_csv_line('', d)
        self.assertIsNone(result)
        self.assertIn("missing", error_msg)

    def test_parse_csv(self):
        regular_data, regular_err = self.parse_csv_file("files/csv-import-test.csv")
        self.assertEqual(regular_err, '')

        # With carriage returns
        windows_data, windows_err = self.parse_csv_file("files/windows-csv.csv")
        self.assertEqual(windows_err, '')

    def test_parse_invalid_csv_file(self):
        # csv that has an unlabeled header
        unlabeled_data, unlabeled_err = self.parse_csv_file("files/unlabeled-column.csv")
        self.assertEqual(unlabeled_data, [])
        self.assertNotEqual(unlabeled_err, '')

        # csv that has too many items in the rows compared to the headers
        mismatch_data, mismatch_err = self.parse_csv_file("files/more-entries-than-headers.csv")
        self.assertEqual(mismatch_data, [])
        self.assertNotEqual(mismatch_err, '')

    def test_parse_csv_file_duplicates(self):
        # CSV file with duplicates
        duplicate_data, duplicate_err = self.parse_csv_file("files/with-duplicates.csv")
        self.assertEqual(duplicate_data, [])
        self.assertIn("duplicate", duplicate_err)

        # CSV file without duplicates
        no_duplicate_data, no_duplicate_err = self.parse_csv_file("files/without-duplicates2.csv")
        self.assertNotEqual(no_duplicate_data, [])
        self.assertEqual(no_duplicate_err, '')
