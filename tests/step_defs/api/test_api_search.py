# coding=utf-8
"""Search API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_search.feature')


@given(parsers.parse("the Yoda search file API is queried with {file}"), target_fixture="api_response")
def api_search_file(user, file):
    return api_request(
        user,
        "search",
        {"search_string": file, "search_type": "filename", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )


@given(parsers.parse("the Yoda search folder API is queried with {folder}"), target_fixture="api_response")
def api_search_folder(user, folder):
    return api_request(
        user,
        "search",
        {"search_string": folder, "search_type": "folder", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )


@given(parsers.parse("the Yoda search metadata API is queried with {metadata}"), target_fixture="api_response")
def api_search_metadata(user, metadata):
    return api_request(
        user,
        "search",
        {"search_string": metadata, "search_type": "metadata", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )


@given(parsers.parse("the Yoda search folder status API is queried with {status}"), target_fixture="api_response")
def api_search_folder_status(user, status):
    return api_request(
        user,
        "search",
        {"search_string": status, "search_type": "status", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )


@then(parsers.parse("result {result} is found"))
def api_response_contents(api_response, result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check expected result is in search results.
    found = False
    for item in body['data']['items']:
        if item["name"] == result:
            found = True

    assert found
