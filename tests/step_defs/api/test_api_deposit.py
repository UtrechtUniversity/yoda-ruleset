# coding=utf-8
"""Deposit API feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from test_api_research import file_exists, object_exists         # noqa: I201 I202
from conftest import api_request, post_form_data    # noqa: I201 I202

scenarios('../../features/api/api_deposit.feature')


@given('the Yoda deposit path API is queried', target_fixture="api_response")
def api_deposit_path(user):
    return api_request(
        user,
        "deposit_path",
        {}
    )


@given('a file "<file>" is uploaded in "<folder>"', target_fixture="api_response")
def api_deposit_file_upload(user, file, folder):

    return post_form_data(
        user,
        "research/browse/upload",
        {"file": (file, "test"), "filepath": (None, folder)}
    )


# @then('metadata is returned for "<collection>"')
# def metadata_returned(api_response, collection):
#     http_status, body = api_response
#     assert http_status == 200


# @then('deposit path is returned')
# def api_response_contents(api_response):
#     _, body = api_response
#     assert len(body['data']['deposit_path']) > 0
#     assert body['data']['deposit_path'] == "research-initial"


# @given('metadata JSON exists in "<folder>"')
# def api_response(user, folder):
#     http_status, _ = api_request(
#         user,
#         "meta_form_save",
#         {"coll": folder,
#          "metadata": {
#              "links": [{
#                  "rel": "describedby",
#                  "href": "https://yoda.uu.nl/schemas/default-1/metadata.json"
#              }],
#              "Language": "en - English",
#              "Retention_Period": 10,
#              "Creator": [{
#                  "Name": {
#                      "Given_Name": "Test",
#                      "Family_Name": "Test"
#                  },
#                  "Affiliation": ["Utrecht University"],
#                  "Person_Identifier": [{}]
#              }],
#              "Data_Access_Restriction": "Restricted - available upon request",
#              "Title": "Test",
#              "Description": "Test",
#              "Data_Type": "Dataset",
#              "Data_Classification": "Public",
#              "License": "Creative Commons Attribution 4.0 International Public License"
#          }}
#     )
#
#     assert http_status == 200
