# coding=utf-8
"""Search API feature tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session>
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../features/api_search.feature')

@given('the Yoda search file API is queried with "<file>"', target_fixture="api_response")
def api_response(file):
    return api_request(
        "search",
        {"search_string": file, "search_type": "filename", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )

@given('the Yoda search folder API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "search",
        {"search_string": folder, "search_type": "folder", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )

@given('the Yoda search metadata API is queried with "<metadata>"', target_fixture="api_response")
def api_response(metadata):
    return api_request(
        "search",
        {"search_string": metadata, "search_type": "metadata", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )

@given('the Yoda search folder status API is queried with "<status>"', target_fixture="api_response")
def api_response(status):
    return api_request(
        "search",
        {"search_string": status, "search_type": "status", "offset": 0, "limit": "10", "sort_order": "asc", "sort_on": "name"}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code

@then('result "<result>" is found')
def api_response_contents(api_response, result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check expected result is in search results.
    found = False
    for item in body['data']['items']:
        if item["name"] == result:
            found = True

    assert found
