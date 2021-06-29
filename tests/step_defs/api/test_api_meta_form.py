# coding=utf-8
"""Meta form API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    # parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_meta_form.feature')


@given('the Yoda meta form save API is queried with metadata and "<collection>"', target_fixture="api_response")
def api_meta_form_save(user, collection):
    return api_request(
        user,
        "meta_form_save",
        {"coll": collection,
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
             "Title": "Test",
             "Description": "Test",
             "Data_Type": "Dataset",
             "Data_Classification": "Public",
             "License": "Creative Commons Attribution 4.0 International Public License"
         }}
    )


@given('the Yoda meta form load API is queried with "<collection>"', target_fixture="api_response")
def api_meta_form_load(user, collection):
    return api_request(
        user,
        "meta_form_load",
        {"coll": collection}
    )


@then('file "<file>" exists in "<collection>"')
def file_exists(user, file, collection):
    http_status, body = api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )

    assert http_status == 200

    # Check if folder is in browse results of collection.
    found = False
    for item in body['data']['items']:
        if item["name"] == file:
            found = True

    assert found


@then('metadata is returned for "<collection>"')
def metadata_returned(api_response, collection):
    http_status, body = api_response

    assert http_status == 200
