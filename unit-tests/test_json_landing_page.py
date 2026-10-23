"""Unit tests for the schema.org JSON-LD conversion functions of the landing page"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import importlib
import json
import sys
from typing import Dict
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.append('..')
sys.path.append('../util')

# The 'util' package (imported by json_landing_page) depends on iRODS-provided
# modules that are not available when running the unit tests. Mock them
# before importing json_landing_page so it can be imported here.
for _irods_module in ('genquery', 'session_vars', 'irods_types'):
    sys.modules.setdefault(_irods_module, MagicMock())

importlib.import_module('util.rule')

from json_landing_page import (_schema_org_affiliations, _schema_org_date, _schema_org_keywords,  # noqa: E402
                               _schema_org_organization, _schema_org_person,
                               _schema_org_temporal_coverage, create_schema_org_json_ld,
                               persistent_identifier_to_uri)

# Dummy values
DOI_URI = 'https://doi.org/10.1234/yoda-abc12345'
LANDING_PAGE_URL = 'https://public.yoda.test/yoda/vault/abc12345.html'
DOWNLOAD_URL = 'https://public.data.yoda.test/vault-default-3/research-default-3'
PUBLISHER = 'Utrecht University'
KEYWORDS = [{'subject': 'keyword 1'}, {'subject': 'keyword 2'}]
ORCID = 'https://orcid.org/1234-1234-1234-1234'
ISNI = '1234123412341234'
RESEARCHER_ID = 'https://www.researcherid.com/rid/A-1234-2020'
ROR = 'https://ror.org/04pp8hn57'


class JsonLandingPagePersistentIdentifierTest(TestCase):
    """Tests for converting a persistent identifier to a URI"""

    def test_doi(self) -> None:
        """DOI of a data package"""
        self.assertEqual(persistent_identifier_to_uri('DOI', '10.1234/yoda-abc12345'), DOI_URI)

    def test_orcid(self) -> None:
        """ORCID that is stored without its URI"""
        self.assertEqual(persistent_identifier_to_uri('ORCID', '1234-1234-1234-1234'), ORCID)

    def test_identifier_that_is_a_uri(self) -> None:
        """ORCID that is stored as a URI, as default-3 requires"""
        self.assertEqual(persistent_identifier_to_uri('ORCID', ORCID), ORCID)

    def test_identifier_of_another_scheme(self) -> None:
        """Identifier of a scheme that has no resolver does not become a URI"""
        self.assertEqual(persistent_identifier_to_uri('ISNI', ISNI), f'#{ISNI}')


class JsonLandingPageOrganizationTest(TestCase):
    """Tests for converting an organization to schema.org format"""

    def test_name_and_identifier(self) -> None:
        """Organization with a name and an identifier is identified by it"""
        self.assertDictEqual(_schema_org_organization('Utrecht University', ROR),
                             {'@type': 'Organization', 'name': 'Utrecht University',
                              '@id': ROR, 'sameAs': ROR})

    def test_identifier_that_is_not_a_uri(self) -> None:
        """An identifier that does not resolve is left out."""
        self.assertDictEqual(_schema_org_organization('Utrecht University', 'javascript:alert(1)'),
                             {'@type': 'Organization', 'name': 'Utrecht University'})


class JsonLandingPageAffiliationsTest(TestCase):
    """Tests for converting affiliations to schema.org format."""

    def test_affiliation(self) -> None:
        """Affiliation with a name and an identifier"""
        output = _schema_org_affiliations([{'Affiliation_Name': 'Utrecht University',
                                            'Affiliation_Identifier': ROR}])
        self.assertEqual(output, [{'@type': 'Organization', 'name': 'Utrecht University',
                                   '@id': ROR, 'sameAs': ROR}])

    def test_affiliation_without_name(self) -> None:
        """Affiliation without a name is left out, as it is what schema.org needs"""
        self.assertEqual(_schema_org_affiliations([{'Affiliation_Identifier': ROR}]), [])

    def test_affiliation_as_string(self) -> None:
        """Affiliation of an old schema, which is a plain string"""
        self.assertEqual(_schema_org_affiliations(['Utrecht University']),
                         [{'@type': 'Organization', 'name': 'Utrecht University'}])


class JsonLandingPagePersonTest(TestCase):
    """Tests for converting a creator to schema.org format"""

    def test_creator(self) -> None:
        """Creator of a default-3 data package, with an ORCID and an affiliation"""
        output = _schema_org_person({'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                     'Person_Identifier': [{'Name_Identifier_Scheme': 'ORCID',
                                                            'Name_Identifier': ORCID}],
                                     'Affiliation': [{'Affiliation_Name': 'Utrecht University'}]})
        self.assertDictEqual(output, {'@type': 'Person', 'name': 'Jane Doe',
                                      '@id': ORCID, 'sameAs': [ORCID],
                                      'affiliation': [{'@type': 'Organization',
                                                       'name': 'Utrecht University'}]})

    def test_name_as_string(self) -> None:
        """Creator of an older schema, whose name is a single string"""
        self.assertEqual(_schema_org_person({'Name': 'Jane Doe'})['name'], 'Jane Doe')

    def test_empty_name(self) -> None:
        """Creator whose name is empty gets an empty name, which the caller leaves out"""
        self.assertEqual(_schema_org_person({'Name': {'Given_Name': '', 'Family_Name': ''}})['name'], '')

    def test_first_resolvable_identifier(self) -> None:
        """Creator is identified by the first identifier that resolves"""
        output = _schema_org_person({'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                     'Person_Identifier': [{'Name_Identifier_Scheme': 'ISNI',
                                                            'Name_Identifier': ISNI},
                                                           {'Name_Identifier_Scheme': 'ORCID',
                                                            'Name_Identifier': ORCID}]})
        self.assertEqual(output['@id'], ORCID)

    def test_every_resolvable_identifier_is_kept(self) -> None:
        """Creator with several identifiers keeps all that resolve, and is identified by the first"""
        output = _schema_org_person({'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                     'Person_Identifier': [{'Name_Identifier_Scheme': 'ORCID',
                                                            'Name_Identifier': ORCID},
                                                           {'Name_Identifier_Scheme': 'Author identifier (Scopus)',
                                                            'Name_Identifier': '12345678900'},
                                                           {'Name_Identifier_Scheme': 'ResearcherID (Web of Science)',
                                                            'Name_Identifier': RESEARCHER_ID}]})
        self.assertEqual(output['@id'], ORCID)
        self.assertEqual(output['sameAs'], [ORCID, RESEARCHER_ID])

    def test_affiliation_as_string(self) -> None:
        """Creator of an older schema, whose affiliation is a string instead of a list"""
        output = _schema_org_person({'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                                     'Affiliation': 'Utrecht University'})
        self.assertEqual(output['affiliation'], [{'@type': 'Organization', 'name': 'Utrecht University'}])

    def test_creator_without_identifier_and_affiliation(self) -> None:
        """Creator of a schema that has neither an identifier nor an affiliation"""
        output = _schema_org_person({'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'}})
        self.assertDictEqual(output, {'@type': 'Person', 'name': 'Jane Doe'})


class JsonLandingPageKeywordsTest(TestCase):
    """Tests for converting the keywords of the landing page to schema.org format"""

    def test_keywords(self) -> None:
        """Keywords are as the landing page collects them"""
        self.assertEqual(_schema_org_keywords(KEYWORDS), ['keyword 1', 'keyword 2'])

    def test_duplicates(self) -> None:
        """Duplicate keywords are reduced to one"""
        self.assertEqual(_schema_org_keywords([{'subject': 'keyword 1'}, {'subject': 'keyword 2'},
                                               {'subject': 'keyword 1'}]),
                         ['keyword 1', 'keyword 2'])

    def test_tree_keyword(self) -> None:
        """Keyword of epos-msl, of which only the subject is used."""
        self.assertEqual(_schema_org_keywords([{'subject': 'keyword 1',
                                                'subjectScheme': 'EPOS-MSL',
                                                'valueUri': 'https://epos-msl.uu.nl/voc/keyword-1'}]),
                         ['keyword 1'])

    def test_values_that_are_not_keywords(self) -> None:
        """A keyword without a subject, and the vocabulary path of a geo field, are left out"""
        self.assertEqual(_schema_org_keywords([{'subject': ''},
                                               'keyword 1 -> keyword 2 -> keyword 3']), [])


class JsonLandingPageDateTest(TestCase):
    """Tests for converting a date of the metadata to a schema.org date"""

    def test_date(self) -> None:
        """Date of a collection period"""
        self.assertEqual(_schema_org_date('2026-01-01'), '2026-01-01')

    def test_timestamp(self) -> None:
        """Timestamp of the publication date keeps only the date"""
        self.assertEqual(_schema_org_date('2026-01-01T12:00:00.000000'), '2026-01-01')

    def test_unusable_date(self) -> None:
        """A date that cannot be parsed gives no date, left out"""
        self.assertEqual(_schema_org_date('sometime in 2026'), '')

    def test_without_date(self) -> None:
        """Metadata without a date gives no date"""
        self.assertEqual(_schema_org_date(''), '')


class JsonLandingPageTemporalCoverageTest(TestCase):
    """Tests for converting the collection period of a data package to temporal coverage"""

    def test_collection_period(self) -> None:
        """Collection period with a start date and an end date"""
        output = _schema_org_temporal_coverage({'Collected': {'Start_Date': '2026-01-01',
                                                              'End_Date': '2026-12-31'}})
        self.assertEqual(output, '2026-01-01/2026-12-31')

    def test_one_date_only(self) -> None:
        """One date means the metadata is wrong, rather than the period being open-ended."""
        self.assertEqual(_schema_org_temporal_coverage({'Collected': {'Start_Date': '2026-01-01'}}), '')

    def test_without_collection_period(self) -> None:
        """Data package of a schema that has no collection period"""
        self.assertEqual(_schema_org_temporal_coverage({}), '')


class JsonLandingPageSchemaOrgJsonLdTest(TestCase):
    """Tests for the schema.org JSON-LD block as a whole"""

    @staticmethod
    def _combi() -> Dict:
        """Create combined metadata of a complete, openly available default-3 data package.

        :returns: Combined JSON structure of a data package
        """
        return {'Title': 'Title of the data package',
                'Description': 'Description of the data package',
                'Language': 'en - English',
                'Version': 'version 1',
                'License': 'Creative Commons Attribution 4.0 International Public License',
                'Collected': {'Start_Date': '2026-01-01', 'End_Date': '2026-12-31'},
                'Creator': [{'Name': {'Given_Name': 'Jane', 'Family_Name': 'Doe'},
                             'Person_Identifier': [{'Name_Identifier_Scheme': 'ORCID',
                                                    'Name_Identifier': ORCID}],
                             'Affiliation': [{'Affiliation_Name': 'Utrecht University',
                                              'Affiliation_Identifier': ROR}]}],
                'System': {'License_URI': 'https://creativecommons.org/licenses/by/4.0/legalcode',
                           'Publication_Date': '2026-01-01T12:00:00.000000'}}

    def _block(self, combi: Dict, download_url: str = DOWNLOAD_URL) -> Dict:
        """Create the JSON-LD block of this data package and parse it.

        :param combi:        Combined metadata JSON of the data package
        :param download_url: URL to retrieve the data, empty unless it is openly available

        :returns: The properties of the JSON-LD block
        """
        return json.loads(create_schema_org_json_ld(combi, DOI_URI, KEYWORDS, PUBLISHER,
                                                    LANDING_PAGE_URL, download_url))

    def test_all_properties(self) -> None:
        """Complete metadata of an openly available data package gives every property"""
        self.assertEqual(list(self._block(self._combi())),
                         ['@context', '@type', 'name', 'description', '@id', 'identifier', 'url',
                          'distribution', 'isAccessibleForFree', 'license', 'creator', 'keywords',
                          'version', 'temporalCoverage', 'datePublished', 'publisher', 'inLanguage'])

    def test_values(self) -> None:
        """Properties hold the values of the metadata they are converted from"""
        output = self._block(self._combi())
        self.assertEqual(output['@context'], 'https://schema.org')
        self.assertEqual(output['@type'], 'Dataset')
        self.assertEqual(output['name'], 'Title of the data package')
        self.assertEqual(output['description'], 'Description of the data package')
        self.assertEqual(output['@id'], DOI_URI)
        self.assertEqual(output['identifier'], DOI_URI)
        self.assertEqual(output['url'], LANDING_PAGE_URL)
        self.assertEqual(output['distribution'],
                         [{'@type': 'DataDownload', 'contentUrl': DOWNLOAD_URL}])
        self.assertTrue(output['isAccessibleForFree'])
        self.assertEqual(output['license'], 'https://creativecommons.org/licenses/by/4.0/legalcode')
        self.assertEqual(output['keywords'], ['keyword 1', 'keyword 2'])
        self.assertEqual(output['version'], 'version 1')
        self.assertEqual(output['temporalCoverage'], '2026-01-01/2026-12-31')
        self.assertEqual(output['datePublished'], '2026-01-01')
        self.assertEqual(output['publisher'], {'@type': 'Organization', 'name': PUBLISHER})
        self.assertEqual(output['inLanguage'], 'en')

    def test_creator(self) -> None:
        """Creator keeps its identifier and its affiliation"""
        self.assertEqual(self._block(self._combi())['creator'],
                         [{'@type': 'Person', 'name': 'Jane Doe', '@id': ORCID, 'sameAs': [ORCID],
                           'affiliation': [{'@type': 'Organization', 'name': 'Utrecht University',
                                            '@id': ROR, 'sameAs': ROR}]}])

    def test_not_openly_available(self) -> None:
        """Data that is not openly available gives neither a download nor free access"""
        output = self._block(self._combi(), download_url='')
        self.assertNotIn('distribution', output)
        self.assertNotIn('isAccessibleForFree', output)

    def test_custom_license(self) -> None:
        """A custom license has no URI to point at, so the license is left out"""
        combi = self._combi()
        combi['License'] = 'Custom'
        self.assertNotIn('license', self._block(combi))

    def test_creator_without_name(self) -> None:
        """A creator without a name means the metadata is broken, so it is left out"""
        combi = self._combi()
        combi['Creator'] = [{'Name': {'Given_Name': '', 'Family_Name': ''}}]
        self.assertNotIn('creator', self._block(combi))

    def test_script_element_cannot_be_closed(self) -> None:
        """Special characters are left as JSON escapes."""
        combi = self._combi()
        combi['Title'] = '</script><img src=x onerror=alert(1)>'
        output = create_schema_org_json_ld(combi, DOI_URI, [], PUBLISHER, LANDING_PAGE_URL, '')
        self.assertNotIn('<', output)
        self.assertNotIn('>', output)
        self.assertNotIn('&', output)
        self.assertEqual(json.loads(output)['name'], combi['Title'])

    def test_text_is_not_changed_by_escaping(self) -> None:
        """Escaping keeps the text of the metadata"""
        combi = self._combi()
        combi['Description'] = 'concentrations < 0.5 mg/L & temperature > 30 degrees'
        self.assertEqual(self._block(combi)['description'], combi['Description'])

    def test_text_cannot_add_properties(self) -> None:
        """Text that is JSON-like stays text"""
        combi = self._combi()
        combi['Description'] = '", "isAccessibleForFree": true, "junk": "'
        output = self._block(combi, download_url='')
        self.assertNotIn('isAccessibleForFree', output)
        self.assertNotIn('junk', output)
        self.assertEqual(output['description'], combi['Description'])
