import pytest

from pytest_bdd import scenarios, given, when, then, parsers

from conftest import api_request

scenarios('../features/api_search.feature')

@pytest.fixture
@given('the Yoda file search API is queried with "<file>"')
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
