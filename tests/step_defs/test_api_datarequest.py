import pytest

from pytest_bdd import scenarios, given, when, then, parsers

from conftest import api_request

scenarios('../features/api_datarequest.feature')

@pytest.fixture
@given('the Yoda datarequest API is queried with request "<request_id>"')
def api_response(request_id):
    return api_request(
        "datarequest_get",
        {"request_id": request_id}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code


@then('request is returned with id "<request_id>"')
def api_response_contents(api_response, request_id):
    http_status, body = api_response

    assert len(body['data']) > 0
