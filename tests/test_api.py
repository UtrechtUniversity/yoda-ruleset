#!/usr/bin/env python3
"""Yoda API tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session> -v
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from conftest import api_request


def test_research_file_delete():
    response = api_request(
        "research_file_delete",
        {"coll": "/tempZone/home/research-initial1",
         "file_name": "yoda-metadata.json"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": {"proc_status_info": "", "proc_status": "ok"}})


def test_browse_folder():
    response = api_request(
        "browse_folder",
        {"coll": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": {"total": 0, "items": []}})


def test_meta_form_save():
    response = api_request(
        "meta_form_save",
        {"coll": "/tempZone/home/research-initial1",
         "metadata": {
             "links": [{
                 "rel": "describedby",
                 "href": "https://yoda.uu.nl/schemas/default-1/metadata.json"
             }],
             "Language": "en - English",
             "Retention_Period": 10,
             "Creator": [{
                 "Name": {
                     "Given_Name": "Test",
                     "Family_Name": "Test"
                 },
                 "Affiliation": ["Utrecht University"],
                 "Person_Identifier": [{}]
             }],
             "Data_Access_Restriction": "Restricted - available upon request",
             "Version": "0",
             "Title": "Test",
             "Description": "Test",
             "Data_Type": "Dataset",
             "Data_Classification": "Public",
             "License": "Creative Commons Attribution 4.0 International Public License"
         }}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": None})


def test_folder_lock():
    response = api_request(
        "folder_lock",
        {"coll": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": None})


def test_folder_unlock():
    response = api_request(
        "folder_unlock",
        {"coll": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": None})


def test_folder_submit():
    response = api_request(
        "folder_submit",
        {"coll": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": None})


def test_folder_accept():
    response = api_request(
        "folder_accept",
        {"coll": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": None})


def test_research_collection_details():
    response = api_request(
        "research_collection_details",
        {"path": "/tempZone/home/research-initial1"}
    )

    assert response == (200, {"status": "ok", "status_info": None, "data": {"status": "ACCEPTED", "vault_path": "vault-initial1", "lock_count": 1, "basename": "research-initial1", "member_type": "manager", "is_datamanager": True}})
