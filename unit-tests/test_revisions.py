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
        eligible, msg = revision_eligible(100, True, 2, "/zone/obj", [["research-initial"]], True)
        self.assertTrue(eligible)
        self.assertEquals(msg, "")

        # Data obj does not exist
        eligible, msg = revision_eligible(100, False, None, "/zone/obj", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertIn("was not found", msg)

        # No groups
        eligible, msg = revision_eligible(100, True, 2, "/zone/obj", [], True)
        self.assertFalse(eligible)
        self.assertIn("Cannot find owner", msg)

        # Too many groups
        eligible, msg = revision_eligible(100, True, 2, "/zone/obj", [["research-initial"], ["research-initial1"]], True)
        self.assertFalse(eligible)
        self.assertIn("Cannot find unique owner", msg)

        # Too large data object (not an error)
        eligible, msg = revision_eligible(2, True, "100", "/zone/obj", [["research-initial"]], True)
        self.assertFalse(eligible)
        self.assertEquals(msg, "")

        # No revision store
        eligible, msg = revision_eligible(100, True, 2, "/zone/obj", [["research-initial"]], False)
        self.assertFalse(eligible)
        self.assertIn("Revision store", msg)
        self.assertIn("does not exist", msg)

    def test_revision_strategy(self):
        strategy = get_revision_strategy("B")
        self.assertEquals(len(strategy.get_buckets()), 8)
        self.assertEquals(strategy.get_minimum_bucket_size(), 2)
        # Tests total length of all buckets in seconds; equivalent to roughly 29 weeks.
        self.assertEquals(strategy.get_total_bucket_timespan(), 17755200)

    def test_revision_cleanup_prefilter(self):
        empty_input = []
        empty_output = revision_cleanup_prefilter(None, empty_input, "B", False)
        self.assertEquals(empty_output, [])
        single_input = [[(1, 123, "/foo/bar/baz")]]
        single_output = revision_cleanup_prefilter(None, single_input, "B", False)
        self.assertEquals(single_output, [])  # Does not exceed min. bucket size for strategy B
        two_input = [[(1, 123, "/foo/bar/baz"), (2, 234, "/foo/bar/baz")]]
        two_output = revision_cleanup_prefilter(None, two_input, "B", False)
        # Does not exceed min. bucket size for strategy B
        # But more than 1 revision (so cannot prefilter, because
        # revisions could be outside defined buckets)
        self.assertEquals(two_output, two_input)
        three_input = [[(1, 123, "/foo/bar/baz"), (2, 234, "/foo/bar/baz"), (3, 345, "/foo/bar/baz")]]
        three_output = revision_cleanup_prefilter(None, three_input, "B", False)
        self.assertEquals(three_output, three_input)  # Exceeds min. bucket size for strategy B

    def test_revision_deletion_candidates_empty(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = []
        output = get_deletion_candidates(None, revision_strategy, revisions, dummy_time, False)
        self.assertEquals(output, [])

    def test_revision_deletion_candidates_1_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [])

    def test_revision_deletion_candidates_2_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [])

    def test_revision_deletion_candidates_2_multi_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 13 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [])

    def test_revision_deletion_candidates_4_multi_bucket_no_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 3600 * 16, "/foo/bar/baz"),
                     (4, dummy_time - 3600 * 17, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [])

    def test_revision_deletion_candidates_3_bucket_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [2])

    def test_revision_deletion_candidates_6_buckets_exceed(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 120, "/foo/bar/baz"),
                     (3, dummy_time - 180, "/foo/bar/baz"),
                     (4, dummy_time - 3600 * 16 - 60, "/foo/bar/baz"),
                     (5, dummy_time - 3600 * 16 - 120, "/foo/bar/baz"),
                     (6, dummy_time - 3600 * 16 - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [2, 5])

    def test_revision_deletion_1_before_buckets(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 365 * 24 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [])

    def test_revision_deletion_1_bucket_1_before(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [2])

    def test_revision_deletion_1_bucket_2_before(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600 - 60, "/foo/bar/baz"),
                     (3, dummy_time - 365 * 24 * 3600 - 90, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [2, 3])

    def test_revision_deletion_3_before_buckets(self):
        dummy_time = 1000000000
        revision_strategy = get_revision_strategy("B")
        revisions = [(1, dummy_time - 365 * 24 * 3600 - 60, "/foo/bar/baz"),
                     (2, dummy_time - 365 * 24 * 3600 - 120, "/foo/bar/baz"),
                     (3, dummy_time - 365 * 24 * 3600 - 180, "/foo/bar/baz")]
        output = get_deletion_candidates(None, revision_strategy, revisions, 1000000000, False)
        self.assertEquals(output, [2, 3])
