"""Unit tests for the correctify functions in schema_transformations"""

__copyright__ = 'Copyright (c) 2024-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from schema_transformations_utils import add_affiliation_identifier, correctify_isni, correctify_orcid, correctify_researcher_id, correctify_scopus, merge_geo_keywords, rename_related_datapackage


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


class CorrectifyResearcherIDTest(TestCase):
    def test_correctify_format(self):
        """Test Researher ID with correct format"""
        researcher_id = "https://www.researcherid.com/rid/A-1234-1234"
        self.assertEqual(correctify_researcher_id(researcher_id), researcher_id)

    def test_correctify_invalid_format(self):
        """Test Researher ID with invalid format"""
        researcher_id = "foobar1234"
        self.assertIsNone(correctify_researcher_id(researcher_id))

    def test_orcid_with_spaces(self):
        """Test Researher ID that contains spaces and should be corrected"""
        researcher_id = " https://www.researcherid.com/rid/A-1234-1234    "
        corrected_researcher_id = "https://www.researcherid.com/rid/A-1234-1234"
        self.assertEqual(correctify_researcher_id(researcher_id), corrected_researcher_id)


class AddAffiliationIdentifierTest(TestCase):
    def test_add_affiliation_identifier(self):
        """Test adding affiliation identifiers to creators, contributors, and contacts."""
        original_metadata = {
            "Creator": [{"Affiliation": ["Utrecht University"]}],
            "Contributor": [{"Affiliation": ["Utrecht University"]}],
            "Contact": [{"Affiliation": ["Utrecht University"]}],
        }

        expected_metadata = {
            "Creator": [{"Affiliation": [{"Affiliation_Name": "Utrecht University", "Affiliation_Identifier": ""}]}],
            "Contributor": [{"Affiliation": [{"Affiliation_Name": "Utrecht University", "Affiliation_Identifier": ""}]}],
            "Contact": [{"Affiliation": [{"Affiliation_Name": "Utrecht University", "Affiliation_Identifier": ""}]}],
        }

        self.assertDictEqual(add_affiliation_identifier(original_metadata), expected_metadata)


class MergeGeoKeywordsTest(TestCase):
    def test_merge_geo_keywords(self):
        """Test the merging of geographical keywords into the correct format."""
        original_metadata = {
            "Main_Setting": ["basin plain setting"],
            "Process_Hazard": ["deformation"],
            "Geological_Structure": ["fault"],
            "Geomorphical_Feature": ["alluvial and fluvial features"],
            "Material": ["Air"],
            "Apparatus": ["2D Convection box"],
            "Monitoring": ["Conductivity measuring system"],
            "Software": ["CloudCompare"],
            "Measured_Property": ["Bulk modulus"],
            "Tag": ["keyword"]
        }

        expected_metadata = {
            "TreeKeyword": [
                {"subject": "Air"},
                {"subject": "2D Convection box"},
                {"subject": "Bulk modulus"},
                {"subject": "basin plain setting"},
                {"subject": "Conductivity measuring system"},
                {"subject": "deformation"},
                {"subject": "fault"},
                {"subject": "alluvial and fluvial features"},
                {"subject": "CloudCompare"},
                {"subject": "keyword"}
            ]
        }

        self.assertDictEqual(merge_geo_keywords(original_metadata), expected_metadata)

    def test_merge_geo_keywords_emptye(self):
        """Test the merging of empty geographical keywords into the correct format."""
        original_metadata = {
            "Main_Setting": [],
            "Process_Hazard": [],
            "Geological_Structure": [],
            "Geomorphical_Feature": [],
            "Material": [],
            "Apparatus": [],
            "Monitoring": [],
            "Software": [],
            "Measured_Property": [],
            "Tag": [],
        }

        expected_metadata = {
            "TreeKeyword": []
        }

        self.assertDictEqual(merge_geo_keywords(original_metadata), expected_metadata)


class RenameRelatedDatapackageTest(TestCase):
    def test_rename_related_datapackage(self):
        """Test renaming Related Datapackage field to Related Resource field."""
        original_metadata = {
            "Related_Datapackage": [
                {
                    "Relation_Type": "IsCitedBy",
                    "Title": "RELATED DATAPACKAGE",
                    "Persistent_Identifier": {
                        "Identifier_Scheme": "ARK",
                        "Identifier": "RDP1",
                    },
                }
            ]
        }

        expected_metadata = {
            "Related_Resource": [
                {
                    "Relation_Type": "IsCitedBy",
                    "Title": "RELATED DATAPACKAGE",
                    "Persistent_Identifier": {
                        "Identifier_Scheme": "ARK",
                        "Identifier": "RDP1",
                    },
                }
            ]
        }

        self.assertDictEqual(rename_related_datapackage(original_metadata), expected_metadata)

    def test_rename_related_datapackage_no_field(self):
        """Test if Related_Datapackage is absent, metadata is unchanged (no Related_Resource)."""
        original_metadata = {"Foo_Bar": 1}
        expected_metadata = {"Foo_Bar": 1}
        self.assertDictEqual(rename_related_datapackage(original_metadata), expected_metadata)
