# coding=utf-8
"""Provenance API feature tests.

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

scenarios('../features/api_provenance.feature')

@given('the Yoda provenance log API is queried with "<collection>"', target_fixture="api_response")
def api_response(collection):
    return api_request(
        "provenance_log",
        {"coll": collection}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code

@then('provenance log is returned')
def api_response_contents(api_response):
    _, body = api_response

    assert len(body["data"]) >= 0
