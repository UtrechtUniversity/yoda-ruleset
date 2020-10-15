# coding=utf-8
"""Browse API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../features/api_browse.feature')


@given('the Yoda browse folder API is queried with "<collection>"', target_fixture="api_response")
def api_browse_folder(user, collection):
    return api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )


@given('the Yoda browse collections API is queried with "<collection>"', target_fixture="api_response")
def api_browse_collections(user, collection):
    return api_request(
        user,
        "browse_collections",
        {"coll": collection}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then('the browse result contains "<result>"')
def api_response_contains(api_response, result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check if expected result is in browse results.
    found = False
    for item in body['data']['items']:
        if item["name"] == result:
            found = True

    assert found


@then('the browse result does not contain "<notresult>"')
def api_response_not_contain(api_response, notresult):
    _, body = api_response

    # Check if not expected result is in browse results.
    found = True
    for item in body['data']['items']:
        if item["name"] == notresult:
            found = False

    assert found
