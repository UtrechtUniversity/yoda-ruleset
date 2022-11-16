# coding=utf-8
"""Schema transformations UI feature tests."""

__copyright__ = 'Copyright (c) 2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from collections import OrderedDict
from pathlib import Path

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

from conftest import upload_data

scenarios('../../features/ui/ui_schema_transformations.feature')


@when(parsers.parse("metadata file {schema_from} for {schema_to} is uploaded by user {user}"), target_fixture="api_response")
def ui_schema_transformations_upload_metadata(user, schema_from, schema_to):
    cwd = os.getcwd()

    with open("{}/files/transformations/{}_{}.json".format(cwd, schema_from, schema_to)) as f:
        metadata = f.read()

    return upload_data(
        user,
        "yoda-metadata.json",
        "/research-{}".format(schema_to),
        metadata
    )


@when(parsers.parse("file {file} exists in folder"))
def ui_schema_trans_file_exists(browser, file):
    browser.is_text_present(file)


@when('user opens metadata form')
def ui_schema_trans_metadata_open(browser):
    browser.find_by_css('button.metadata-form').click()


@when('user accepts transformation')
def ui_schema_trans_accept_trans(browser):
    browser.find_by_css('button.transformation-accept').click()
    time.sleep(1)
    browser.back()


@then(parsers.parse("user downloads file {file} and checks contents after transformation to {schema_to} from {schema_from}"))
def ui_schema_trans_download_file(browser, tmpdir, file, schema_to, schema_from):
    link = []
    while len(link) == 0:
        link = browser.find_by_css('button[data-name="{}"]'.format(file))
        if len(link) > 0:
            # Open menu for the file.
            browser.find_by_css('button[data-name="{}"]'.format(file)).click()

            # Click on download link.
            browser.find_by_css('a[data-name="{}"]'.format(file))[0].click()
        else:
            browser.find_by_id('file-browser_next').click()

    # Open the downloaded yoda-metadata.json file.
    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/yoda-metadata.json")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/yoda-metadata.json")

    with open(download_dir) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    # Remove the downloaded yoda-metadata.json file.
    os.remove(download_dir)

    # Check actual content after transformation.
    assert metadata['links'][0]['href'] == "https://yoda.uu.nl/schemas/{}/metadata.json".format(schema_to)
    assert metadata["License"] == "Custom"
    assert metadata["Data_Access_Restriction"] == "Open - freely retrievable"
    assert metadata["Title"] == "API test {}".format(schema_from)
    assert metadata["Description"] == "API test {}".format(schema_from)
    assert metadata["Language"] == "en - English"

    if schema_from == "dag-0":
        assert metadata["Collection_Name"] == "dag0-project"
        assert metadata["Retention_Period"] == 5
        assert metadata["Covered_Geolocation_Place"] == ["eerste loc", "tweede loc"]
        assert metadata["Discipline"] == ["Natural Sciences - Earth and related environmental sciences (1.5)",
                                          "Natural Sciences - Physical sciences (1.3)"]
        assert metadata["Collected"] == {"Start_Date": "2000-01-01", "End_Date": "2010-01-01"}
        assert metadata["Tag"] == ["key1", "key2"]
        # research group has to be converted to a contributer with type ResearchGroup
        assert metadata["Contributor"][1] == {"Affiliation": ["Affiliation"],
                                              "Name": {
                                              "Family_Name": "",
                                              "Given_Name": "Earth sciences - Geochemistry"},
                                              "Contributor_Type": "ResearchGroup"}
    else:
        assert metadata["Data_Classification"] == "Public"

    if schema_from != "default-0":
        assert metadata["Data_Type"] == "Dataset"

    if schema_from != "dag-0" and schema_to == "default-2":
        assert metadata["Tag"] == ["yoda"]
