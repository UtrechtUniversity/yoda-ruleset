"""Unit tests for the DataCite JSON conversion functions"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import importlib
import sys
from typing import Dict, List, Union
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.append('..')
sys.path.append('../util')

# The 'util' package (imported by json_datacite) depends on iRODS-provided
# modules that are not available when running the unit tests. Mock them
# before importing json_datacite so it can be imported here.
for _irods_module in ('genquery', 'session_vars', 'irods_types'):
    sys.modules.setdefault(_irods_module, MagicMock())

# json_datacite refers to the 'rule' module through 'from util import *'. The
# util package does not import its submodules when running the unit tests, so
# import it explicitly to make it available as a util attribute.
importlib.import_module('util.rule')

from json_datacite import _process_affiliations_list, get_contributors, get_creators  # noqa: E402


class JsonDataciteAffiliationsListTest(TestCase):
    """Tests for converting affiliations to DataCite format.

    The metadata schemas accept affiliations without an affiliation name, as
    well as affiliations without an affiliation identifier, so the DataCite
    conversion needs to deal with both.
    """

    def test_name_and_identifier(self) -> None:
        """Affiliation with both a name and an identifier"""
        output = _process_affiliations_list([{'Affiliation_Name': 'Utrecht University',
                                              'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'name': 'Utrecht University',
                                         'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                         'affiliationIdentifierScheme': 'ROR'})

    def test_name_only(self) -> None:
        """Affiliation with a name, but without an identifier"""
        output = _process_affiliations_list([{'Affiliation_Name': 'Utrecht University'}])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'name': 'Utrecht University'})

    def test_identifier_only(self) -> None:
        """Affiliation with an identifier, but without a name"""
        output = _process_affiliations_list([{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                         'affiliationIdentifierScheme': 'ROR'})

    def test_empty_name(self) -> None:
        """Affiliation with an identifier and an empty name"""
        output = _process_affiliations_list([{'Affiliation_Name': '',
                                              'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                         'affiliationIdentifierScheme': 'ROR'})

    def test_empty_identifier(self) -> None:
        """Affiliation with a name and an empty identifier"""
        output = _process_affiliations_list([{'Affiliation_Name': 'Utrecht University',
                                              'Affiliation_Identifier': ''}])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'name': 'Utrecht University'})

    def test_empty_dict(self) -> None:
        """Affiliation without any subproperties is ignored"""
        self.assertEqual(_process_affiliations_list([{}]), [])

    def test_empty_name_and_identifier(self) -> None:
        """Affiliation with an empty name and an empty identifier is ignored"""
        self.assertEqual(_process_affiliations_list([{'Affiliation_Name': '',
                                                      'Affiliation_Identifier': ''}]), [])

    def test_string(self) -> None:
        """Affiliation of a legacy schema, which is a plain string"""
        output = _process_affiliations_list(['Utrecht University'])
        self.assertEqual(len(output), 1)
        self.assertDictEqual(output[0], {'name': 'Utrecht University'})

    def test_empty_string(self) -> None:
        """Affiliation that is an empty string is ignored"""
        self.assertEqual(_process_affiliations_list(['']), [])

    def test_empty_list(self) -> None:
        """Empty list of affiliations"""
        self.assertEqual(_process_affiliations_list([]), [])

    def test_multiple(self) -> None:
        """Several affiliations, only some of which have a name"""
        output = _process_affiliations_list([{'Affiliation_Name': 'Utrecht University',
                                              'Affiliation_Identifier': 'https://ror.org/04pp8hn57'},
                                             {'Affiliation_Identifier': 'https://ror.org/123456789'},
                                             {'Affiliation_Name': 'Other organization'},
                                             {},
                                             ''])
        self.assertEqual(output, [{'name': 'Utrecht University',
                                   'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                   'affiliationIdentifierScheme': 'ROR'},
                                  {'affiliationIdentifier': 'https://ror.org/123456789',
                                   'affiliationIdentifierScheme': 'ROR'},
                                  {'name': 'Other organization'}])


class JsonDataciteCreatorTest(TestCase):
    """Tests for converting creators to DataCite format"""

    @staticmethod
    def _combi(affiliation: Union[str, List]) -> Dict:
        """Create combined metadata with a single creator with this affiliation.

        :param affiliation: Value of the Affiliation field of the creator

        :returns: Combined JSON structure with a single creator
        """
        return {'Creator': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                             'Affiliation': affiliation}]}

    def test_no_creators(self) -> None:
        """Combined metadata without creators"""
        self.assertEqual(get_creators({}), [])

    def test_affiliation_without_name(self) -> None:
        """Creator with an affiliation that only has an identifier"""
        output = get_creators(self._combi([{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                                     'affiliationIdentifierScheme': 'ROR'}])

    def test_affiliation_without_identifier(self) -> None:
        """Creator with an affiliation that only has a name"""
        output = get_creators(self._combi([{'Affiliation_Name': 'Utrecht University'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_affiliation_single_string(self) -> None:
        """Creator with an affiliation that is a single string instead of a list"""
        output = get_creators(self._combi('Utrecht University'))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_affiliation_missing(self) -> None:
        """Creator without an affiliation field"""
        output = get_creators({'Creator': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'}}]})
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [])

    def test_multiple(self) -> None:
        """Two creators, one with and one without an affiliation name"""
        combi = {'Creator': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                              'Affiliation': [{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}]},
                             {'Name': {'Given_Name': 'John', 'Family_Name': 'Doe'},
                              'Affiliation': [{'Affiliation_Name': 'Utrecht University'}]}]}
        output = get_creators(combi)
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                                     'affiliationIdentifierScheme': 'ROR'}])
        self.assertEqual(output[1]['affiliation'], [{'name': 'Utrecht University'}])


class JsonDataciteContributorTest(TestCase):
    """Tests for converting contributors to DataCite format"""

    @staticmethod
    def _combi(affiliation: Union[str, List]) -> Dict:
        """Create combined metadata with a single contributor with this affiliation.

        :param affiliation: Value of the Affiliation field of the contributor

        :returns: Combined JSON structure with a single contributor
        """
        return {'Contributor': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                 'Contributor_Type': 'DataCurator',
                                 'Affiliation': affiliation}]}

    def test_no_contributors(self) -> None:
        """Combined metadata without contributors"""
        self.assertEqual(get_contributors({}), [])

    def test_affiliation_without_name(self) -> None:
        """Contributor with an affiliation that only has an identifier"""
        output = get_contributors(self._combi([{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                                     'affiliationIdentifierScheme': 'ROR'}])

    def test_affiliation_without_identifier(self) -> None:
        """Contributor with an affiliation that only has a name"""
        output = get_contributors(self._combi([{'Affiliation_Name': 'Utrecht University'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_affiliation_empty_dict(self) -> None:
        """Contributor with an affiliation without any subproperties"""
        output = get_contributors(self._combi([{}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [])

    def test_affiliation_single_string(self) -> None:
        """Contributor with an affiliation that is a single string instead of a list"""
        output = get_contributors(self._combi('Utrecht University'))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_affiliation_missing(self) -> None:
        """Contributor without an affiliation field"""
        combi = {'Contributor': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                  'Contributor_Type': 'DataCurator'}]}
        output = get_contributors(combi)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [])


class JsonDataciteContactPersonTest(TestCase):
    """Tests for converting contact persons to DataCite format"""

    @staticmethod
    def _combi(affiliation: Union[str, List]) -> Dict:
        """Create combined metadata with a single contact person with this affiliation.

        :param affiliation: Value of the Affiliation field of the contact person

        :returns: Combined JSON structure with a single contact person
        """
        return {'ContactPerson': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                   'Affiliation': affiliation}]}

    def test_affiliation_without_name(self) -> None:
        """Contact person with an affiliation that only has an identifier"""
        output = get_contributors(self._combi([{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                                     'affiliationIdentifierScheme': 'ROR'}])

    def test_affiliation_without_identifier(self) -> None:
        """Contact person with an affiliation that only has a name"""
        output = get_contributors(self._combi([{'Affiliation_Name': 'Utrecht University'}]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_affiliation_single_string(self) -> None:
        """Contact person with an affiliation that is a single string instead of a list"""
        output = get_contributors(self._combi('Utrecht University'))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['affiliation'], [{'name': 'Utrecht University'}])

    def test_contributor_and_contact_person(self) -> None:
        """Both a contributor and a contact person, each with an affiliation without a name"""
        combi = {'Contributor': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                  'Contributor_Type': 'DataCurator',
                                  'Affiliation': [{'Affiliation_Identifier': 'https://ror.org/04pp8hn57'}]}],
                 'ContactPerson': [{'Name': {'Given_Name': 'John', 'Family_Name': 'Doe'},
                                    'Affiliation': [{'Affiliation_Identifier': 'https://ror.org/123456789'}]}]}
        output = get_contributors(combi)
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0]['contributorType'], 'DataCurator')
        self.assertEqual(output[0]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/04pp8hn57',
                                                     'affiliationIdentifierScheme': 'ROR'}])
        self.assertEqual(output[1]['contributorType'], 'Contact')
        self.assertEqual(output[1]['affiliation'], [{'affiliationIdentifier': 'https://ror.org/123456789',
                                                     'affiliationIdentifierScheme': 'ROR'}])
