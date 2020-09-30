# coding=utf-8
"""Search feature tests."""

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../features/api_search.feature')

@given('the Yoda file search API is queried with "<file>"', target_fixture="api_response")
def api_response(file):
    return api_request(
        "search",
        {"search_string":"yoda-metadata.json","search_type":"filename","offset":0,"limit":"10","sort_order":"asc","sort_on":"name"}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code

@then('results are returned for "<file>"')
def api_response_contents(api_response, file):
    http_status, body = api_response

    assert len(body['data']['items']) > 0
