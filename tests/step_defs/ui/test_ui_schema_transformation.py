# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from collections import OrderedDict
from pathlib import Path

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import upload_data

scenarios('../../features/ui/ui_schema_transformation.feature')


@given(parsers.parse("metadata file <schema_from> for <schema_to> is uploaded by user {user}"), target_fixture="api_response")
def api_schema_trans_upload_metadata(user, schema_from, schema_to):
    cwd = os.getcwd()
    with open("{}\\files\\transformations\\{} to {}\\yoda-metadata.json".format(cwd, schema_from, schema_to)) as f:
        metadata = f.read()

    return upload_data(
        user,
        "yoda-metadata.json",
        "/research-{}".format(schema_to),
        metadata
    )


@then(parsers.parse("user browses to research with active metadata schema <schema_to>"))
@when(parsers.parse("user browses to research with active metadata schema <schema_to>"))
def ui_schema_trans_subfolder(browser, schema_to):
    browser.links.find_by_partial_text('research-{}'.format(schema_to)).click()


@then(parsers.parse("file {file} exists in folder"))
def ui_schema_trans_file_exists(browser, file):
    browser.is_text_present(file)


@when('user opens metadata form')
def ui_schema_trans_metadata_open(browser):
    browser.find_by_css('button.metadata-form').click()
    # time.sleep(1)


@when('user accepts transformation')
def ui_schema_trans_accept_trans(browser):
    browser.find_by_css('button.transformation-accept').click()
    time.sleep(1)


@when('user closes metadata form')
def ui_schema_trans_close_metadata_form(browser):
    browser.back()


@when(parsers.parse("user downloads file {file} and checks contents after transformation to <schema_to>"))
def ui_schema_trans_download_file(browser, tmpdir, file, schema_to):
    # open menu for the file
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()

    # Click on download link
    browser.find_by_css('a[data-name="{}"]'.format(file))[0].click()

    # Open the downloaded yoda-metadata.json file
    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    with open("{}\\yoda-metadata.json".format(download_dir)) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    # check actual content after transformation
    assert metadata['links'][0]['href'] == "https://yoda.uu.nl/schemas/{}/metadata.json".format(schema_to)
    assert metadata["License"] == "Custom"
    assert metadata["Data_Access_Restriction"] == "Open - freely retrievable"
    assert metadata["Title"] == "title dag-0"
    assert metadata["Description"] == "descript dag-0"
    assert metadata["Collection_Name"] == "dag0-project"
    assert metadata["Retention_Period"] == 5
    assert metadata["Data_Classification"] == "Sensitive"
    assert metadata["Covered_Geolocation_Place"] == ["eerste loc", "tweede loc"]
    assert metadata["Data_Type"] == "Dataset"
    assert metadata["Discipline"] == ["Natural Sciences - Earth and related environmental sciences (1.5)",
                                      "Natural Sciences - Physical sciences (1.3)"]
    assert metadata["Language"] == "en - English"
    assert metadata["Collected"] == {"Start_Date": "2000-01-01", "End_Date": "2010-01-01"}
    assert metadata["Tag"] == ["key1", "key2"]
    # research group has to be converted to a contributer with type ResearchGroup
    assert metadata["Contributor"][1] == {
            "Affiliation": [
                "Affiliation"
            ],
            "Name": {
                "Family_Name": "",
                "Given_Name": "Earth sciences - Geochemistry"
            },
            "Contributor_Type": "ResearchGroup"}

