"""Unit tests for publication functions"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')
sys.path.append('../util')

from publication_utils import is_latest_version, should_abort
from util.constants import publication_status


class PublicationUtilsTest(TestCase):
    def test_is_latest_version_true(self):
        publication_state = {
            "previous_version": "/tempZone/vault-test/vault-test-version-1[-446090160]",
        }
        self.assertTrue(is_latest_version(publication_state))

    def test_is_latest_version_false_when_next_version_exists(self):
        publication_state = {
            "previous_version": "/tempZone/vault-test/vault-test-version-1[-446090160]",
            "next_version": "/tempZone/vault-test/vault-test-version-2[1781863101]",
        }
        self.assertFalse(is_latest_version(publication_state))

    def test_is_latest_version_false_when_previous_version_missing(self):
        publication_state = {
            "next_version": "/tempZone/vault-test/vault-test-version-2[1781863101]",
        }
        self.assertFalse(is_latest_version(publication_state))

    def test_is_latest_version_false_when_previous_version_is_none(self):
        publication_state = {
            "previous_version": None,
            "next_version": None,
        }
        self.assertFalse(is_latest_version(publication_state))

    def test_should_abort_true_for_unrecoverable(self):
        self.assertTrue(should_abort(publication_status.UNRECOVERABLE))

    def test_should_abort_true_for_retry(self):
        self.assertTrue(should_abort(publication_status.RETRY))

    def test_should_abort_false_for_processing(self):
        self.assertFalse(should_abort(publication_status.PROCESSING))

    def test_should_abort_false_for_ok(self):
        self.assertFalse(should_abort(publication_status.OK))

    def test_should_abort_false_for_unknown(self):
        self.assertFalse(should_abort(publication_status.UNKNOWN))
