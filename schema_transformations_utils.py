"""JSON schema transformation utility functions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from typing import Any, Dict, List


def add_affiliation_identifier(m: Dict[str, Any]) -> Dict[str, Any]:
    """Add affiliation identifiers to creators, contributors, and contacts.

    :param m: Metadata to transform

    :returns: Transformed JSON object
    """
    def _transform_affiliations(entities: List[Dict[str, Any]]) -> None:
        """Transform affiliations for a list of entities."""
        for entity in entities:
            new_affiliations = []
            for affiliation in entity.get('Affiliation', []):
                new_affiliations.append({"Affiliation_Name": affiliation, "Affiliation_Identifier": ""})
            entity['Affiliation'] = new_affiliations

    # Transform affiliations for creators, contributors, and contacts
    if 'Creator' in m:
        _transform_affiliations(m['Creator'])

    if 'Contributor' in m:
        _transform_affiliations(m['Contributor'])

    if 'Contact' in m:
        _transform_affiliations(m['Contact'])

    return m


def correctify_isni(org_isni: str) -> str | None:
    """Correct ill-formatted ISNI."""
    # Remove all spaces.
    new_isni = org_isni.replace(' ', '')

    # Upper-case X.
    new_isni = new_isni.replace('x', 'X')

    # The last part should hold a valid id like eg: 123412341234123X.
    # If not, it is impossible to correct it to the valid isni format
    new_isni_split = new_isni.split('/')
    if not re.search("^[0-9]{15}[0-9X]$", new_isni_split[-1]):
        return None

    return "https://isni.org/isni/{}".format(new_isni_split[-1])


def correctify_orcid(org_orcid: str) -> str | None:
    """Correct illformatted ORCID."""
    # Get rid of all spaces.
    orcid = org_orcid.replace(' ', '')

    # Upper-case X.
    orcid = orcid.replace('x', 'X')

    # The last part should hold a valid id like eg: 1234-1234-1234-123X.
    # If not, it is impossible to correct it to the valid orcid format
    orcs = orcid.split('/')
    if not re.search("^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcs[-1]):
        return None

    return "https://orcid.org/{}".format(orcs[-1])


def correctify_scopus(org_scopus: str) -> str | None:
    """Correct illformatted Scopus."""
    # Get rid of all spaces.
    new_scopus = org_scopus.replace(' ', '')

    if not re.search(r"^\d{1,11}$", new_scopus):
        return None

    return new_scopus


def correctify_researcher_id(org_researcher_id: str) -> str | None:
    """Correct illformatted ResearcherID."""
    # Get rid of all spaces.
    researcher_id = org_researcher_id.replace(' ', '')

    # The last part should hold a valid id like eg: A-1234-1234
    # If not, it is impossible to correct it to the valid ResearcherID format
    rid = researcher_id.split('/')
    if not re.search("^[A-Z]-[0-9]{4}-[0-9]{4}$", rid[-1]):
        return None

    return "https://www.researcherid.com/rid/{}".format(rid[-1])


def correctify_personal_identifiers(m: Dict[str, Any]) -> Dict[str, Any]:
    """Correct illformatted personal identifiers for creators, contributors, and contacts.

    :param m: Metadata to transform

    :returns: Transformed JSON object
    """
    def _correctify_identifiers(entities: List[Dict[str, Any]]) -> None:
        """Correctify personal identifiers."""
        for entity in entities:
            person_identifiers = []
            for pid in entity.get('Person_Identifier', []):
                scheme = pid.get("Name_Identifier_Scheme")
                value = pid.get("Name_Identifier")

                if not scheme or not value:
                    continue

                corrected_value = None
                if scheme == 'ORCID':
                    # Check for incorrect ORCID format.
                    if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", value):
                        corrected_value = correctify_orcid(value)
                elif scheme == 'Author identifier (Scopus)':
                    # Check for incorrect Scopus format.
                    if not re.search(r"^\d{1,11}$", value):
                        corrected_value = correctify_scopus(value)
                elif scheme == 'ISNI':
                    # Check for incorrect ISNI format.
                    if not re.search("^(https://isni.org/isni/)[0-9]{15}[0-9X]$", value):
                        corrected_value = correctify_isni(value)
                elif scheme == 'ResearcherID (Web of Science)':
                    # Check for incorrect ResearcherID format.
                    if not re.search("^(https://www.researcherid.com/rid/)[A-Z]-[0-9]{4}-[0-9]{4}$", value):
                        corrected_value = correctify_researcher_id(value)

                final_value = corrected_value if corrected_value is not None else value
                if final_value:
                    person_identifiers.append({"Name_Identifier_Scheme": scheme, "Name_Identifier": final_value})

            if len(person_identifiers) > 0:
                entity['Person_Identifier'] = person_identifiers

    # Correctify personal identifiers for creators, contributors, and contacts.
    if 'Creator' in m:
        _correctify_identifiers(m['Creator'])

    if 'Contributor' in m:
        _correctify_identifiers(m['Contributor'])

    if 'Contact' in m:
        _correctify_identifiers(m['Contact'])

    return m


def merge_geo_keywords(m: Dict) -> Dict:
    """Merge several geo keywords into single keyword field.

    :param m: Metadata to transform

    :returns: Transformed JSON object
    """
    tree_keywords = []
    keys_to_merge = [
        'Material',
        'Apparatus',
        'Measured_Property',
        'Main_Setting',
        'Monitoring',
        'Process_Hazard',
        'Geological_Structure',
        'Geomorphical_Feature',
        'Geomorphological_Feature',
        'Software',
        'Tag'
    ]

    # Append each keyword and remove it from the original metadata.
    for key in keys_to_merge:
        if key in m:
            for subject in m[key]:
                tree_keywords.append({"subject": subject})
            m.pop(key)

    m['TreeKeyword'] = tree_keywords
    return m


def rename_related_datapackage(m: Dict) -> Dict:
    """Rename Related Datapackage field to Related Resource field.

    :param m: Metadata to transform

    :returns: Transformed JSON object
    """
    if isinstance(m.get('Related_Datapackage'), list):
        resources = []

        for resource in m['Related_Datapackage']:
            # Only use the identifier regarding relation type.
            if 'Relation_Type' in resource:
                resource['Relation_Type'] = resource['Relation_Type'].split(':')[0]
            resources.append(resource)

        m['Related_Resource'] = resources
        m.pop('Related_Datapackage')

    return m
