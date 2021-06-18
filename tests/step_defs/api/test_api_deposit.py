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

from conftest import api_request

scenarios('../../features/api/api_deposit.feature')


@given('the Yoda deposit path API is queried', target_fixture="api_response")
def api_search_file(user):
    return api_request(
        user,
        "deposit_path",
        {}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then('deposit path is returned')
def api_response_contents(api_response):
    _, body = api_response

    assert len(body['data']['deposit_path']) > 0

    assert body['data']['deposit_path'] == "research-initial"
