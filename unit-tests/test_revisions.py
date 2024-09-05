# -*- coding: utf-8 -*-
"""Unit tests for the revision functions"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from revision_strategies import get_revision_strategy
from revision_utils import get_deletion_candidates, revision_cleanup_prefilter, revision_eligible


class RevisionTest(TestCase):

    def test_revision_eligible(self):
        # Happy flow
        eligible, msg = revision_eligible(100, True, 2, "/zone/home/research-test/obj", [["research-initial"]], True)
        self.assertTrue(eligible)
        self.assertEqual(msg, "")

        # Data obj does not exist
        eligible, msg = revision_eligible(100, False, None, "/zone/home/research-test/obj", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertIn("was not found", msg)

        # No groups
        eligible, msg = revision_eligible(100, True, 2, "/zone/home/research-test/obj", [], True)
        self.assertFalse(eligible)
        self.assertIn("Cannot find owner", msg)

        # Too many groups
        eligible, msg = revision_eligible(100, True, 2, "/zone/home/research-test/obj", [["research-initial"], ["research-initial1"]], True)
        self.assertFalse(eligible)
        self.assertIn("Cannot find unique owner", msg)

        # No revision store
        eligible, msg = revision_eligible(100, True, 2, "/zone/home/research-test/obj", [["research-initial"]], False)
        self.assertFalse(eligible)
        self.assertIn("Revision store", msg)
        self.assertIn("does not exist", msg)

        # Not in research space
        eligible, msg = revision_eligible(100, True, "5", "/zone/home/vault-test/obj", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertEqual(msg, "")

        # Blocklist file
        eligible, msg = revision_eligible(100, True, 2, "/zone/home/research-test/.DS_Store", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertEqual(msg, "")

        # Too large data object (not an error)
        eligible, msg = revision_eligible(2, True, "100", "/zone/home/research-test/obj", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertEqual(msg, "")

    def test_revision_strategy(self):
        strategy = get_revision_strategy("B")
        self.assertEqual(len(strategy.get_buckets()), 8)
        self.assertEqual(strategy.get_minimum_bucket_size(), 2)
        # Tests total length of all buckets in seconds; equivalent to roughly 29 weeks.
        self.assertEqual(strategy.get_total_bucket_timespan(), 17755200)

    def test_revision_cleanup_prefilter_empty(self):
        empty_input = []
        empty_output = revision_cleanup_prefilter(None, empty_input, "B", dict(), False)
        self.assertEqual(empty_output, [])

    def test_revision_cleanup_prefilter_single_exists(self):
        single_input = [[(1, 123, "/foo/bar/baz")]]
        exists_dict = {"/foo/bar/baz": True}
        single_output = revision_cleanup_prefilter(None, single_input, "B", exists_dict, False)
        self.assertEqual(single_output, [])  # Does not exceed min. bucket size for strategy B

    def test_revision_cleanup_prefilter_single_doesnotexist(self):
        single_input = [[(1, 123, "/foo/bar/baz")]]
        exists_dict = {"/foo/bar/baz": False}
        single_output = revision_cleanup_prefilter(None, single_input, "B", exists_dict, False)
        # Do not prefilter if versioned data object no longer exists
        self.assertEqual(single_output, single_input)

    def test_revision_cleanup_prefilter_two_exists(self):
        two_input = [[(1, 123, "/foo/bar/baz"), (2, 234, "/foo/bar/baz")]]
        exists_dict = {"/foo/bar/baz": True}
        two_output = revision_cleanup_prefilter(None, two_input, "B", exists_dict, False)
        # Does not exceed min. bucket size for strategy B
        # But more than 1 revision (so cannot prefilter, because
        # revisions could be outside defined buckets)
        self.assertEqual(two_output, two_input)

    def test_revision_cleanup_prefilter_two_doesnotexist(self):
        exists_dict = {"/foo/bar/baz": False}
        two_input = [[(1, 123, "/foo/bar/baz"), (2, 234, "/foo/bar/baz")]]
        two_output = revision_cleanup_prefilter(None, two_input, "B", exists_dict, False)
        # Do not prefilter if versioned data object no longer exists
        self.assertEqual(two_output, two_input)

    def test_revision_cleanup_prefilter_three(self):
        three_input = [[(1, 123, "/foo/bar/baz"), (2, 234, "/foo/bar/baz"), (3, 345, "/foo/bar/baz")]]
        exists_dict = {"/foo/bar/baz": True}
        three_output = revision_cleanup_prefilter(None, three_input, "B", exists_dict, False)
        self.assertEqual(three_output, three_input)  # Exceeds min. bucket size for strategy B

    def test_revision_deletion_candidates_empty(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = []
        output = get_deletion_candidates(None, revision_strategy, revisions, dummy_time, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_candidates_1_bucket_no_exceed_exists(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_candidates_1_bucket_no_exceed_doesnotexist(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False, False)
        self.assertEqual(output, [1])

    def test_revision_deletion_candidates_2_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_candidates_2_multi_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 13 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_candidates_4_multi_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 3600 * 16, "/foo/bar/baz"),
                     (4, dummy_time - 3600 * 17, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_candidates_3_bucket_exceed_exists(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [2])

    def test_revision_deletion_candidates_3_bucket_exceed_doesnotexist(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False, False)
        self.assertEqual(output, [1, 2, 3])

    def test_revision_deletion_candidates_6_buckets_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 180, "/foo/bar/baz"),
                     (4, dummy_time - 3600 * 16 - 60, "/foo/bar/baz"),
                     (5, dummy_time - 3600 * 16 - 120, "/foo/bar/baz"),
                     (6, dummy_time - 3600 * 16 - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [2, 5])

    def test_revision_deletion_1_before_buckets(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 365 * 24 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [])

    def test_revision_deletion_1_bucket_1_before(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [2])

    def test_revision_deletion_1_bucket_2_before(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600 - 60, "/foo/bar/baz"),
                     (3, dummy_time - 365 * 24 * 3600 - 90, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [2, 3])

    def test_revision_deletion_3_before_buckets(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 365 * 24 * 3600 - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600 - 120, "/foo/bar/baz"),
                     (3, dummy_time - 365 * 24 * 3600 - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, True, False)
        self.assertEqual(output, [2, 3])
