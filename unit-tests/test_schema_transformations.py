# -*- coding: utf-8 -*-
"""Unit tests for the correctify functions in schema_transformations"""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from schema_transformations_utils import correctify_isni, correctify_orcid, correctify_researcher_id, correctify_scopus


class CorrectifyIsniTest(TestCase):
    def test_isni_correct_format(self):
        """Test ISNI with correct format"""
        isni = "https://isni.org/isni/1234123412341234"
        self.assertEqual(correctify_isni(isni), isni)


    def test_isni_correct_format_containing_x(self):
        """Test ISNI with correct format"""
        isni = "https://isni.org/isni/123412341234123x"
        correct_isni = "https://isni.org/isni/123412341234123X"
        self.assertEqual(correctify_isni(isni), correct_isni)


    def test_isni_invalid_format(self):
        """Test ISNI with invalid format (1 less number)"""
        isni = "123412341234123"
        self.assertIsNone(correctify_isni(isni))


    def test_isni_malformed_format(self):
        """Test ISNI with invalid format"""
        isni = "foobar0123456789"
        self.assertIsNone(correctify_isni(isni))


    def test_isni_with_spaces(self):
        """Test ISNI that contains spaces and should be corrected"""
        isni = " https://isni.org/isni/123412341234123x    "
        corrected_isni = "https://isni.org/isni/123412341234123X"
        self.assertEqual(correctify_isni(isni), corrected_isni)


class CorrectifyOrcidTest(TestCase):
    def test_orcid_correct_format(self):
        """Test ORCID with correct format"""
        orcid = "https://orcid.org/1234-1234-1234-1234"
        self.assertEqual(correctify_orcid(orcid), orcid)


    def test_orcid_correct_format_containing_x(self):
        """Test ORCID with correct format"""
        orcid = "https://orcid.org/1234-1234-1234-123x"
        correct_orcid = "https://orcid.org/1234-1234-1234-123X"
        self.assertEqual(correctify_orcid(orcid), correct_orcid)

        
    def test_orcid_invalid_format(self):
        """Test ORCID with invalid format (1 less number)"""
        orcid = "1234-1234-1234-123"
        self.assertIsNone(correctify_orcid(orcid))


    def test_orcid_malformed_format(self):
        """Test ORCID with invalid format"""
        orcid = "1234-foo-bar-1234"
        self.assertIsNone(correctify_orcid(orcid))


    def test_orcid_with_spaces(self):
        """Test ORCID that contains spaces and should be corrected"""
        orcid = " https://orcid.org/1234-1234-1234-123x    "
        corrected_orcid = "https://orcid.org/1234-1234-1234-123X"
        self.assertEqual(correctify_orcid(orcid), corrected_orcid)


class CorrectifyScopusTest(TestCase):
    def test_correctify_format(self):
        """Test SCOPUS with correct format"""
        scopus = "12345678901"
        self.assertEqual(correctify_scopus(scopus), scopus)

    
    def test_correctify_invalid_format(self):
        """Test SCOPUS with invalid format"""
        scopus = "123456789012"
        self.assertIsNone(correctify_scopus(scopus))


    def test_malformed_format(self):
        """Test SCOPUS with invalid format"""
        scopus = "foobar1234"
        self.assertIsNone(correctify_scopus(scopus))


    def test_orcid_with_spaces(self):
        """Test SCOPUS that contains spaces and should be corrected"""
        scopus = " 01234567890    "
        corrected_scopus = "01234567890"
        self.assertEqual(correctify_scopus(scopus), corrected_scopus)
