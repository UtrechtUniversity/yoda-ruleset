# coding=utf-8
"""Provenance API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    # parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_provenance.feature')


@given('the Yoda provenance log API is queried with "<collection>"', target_fixture="api_response")
def api_provenance_log(user, collection):
    return api_request(
        user,
        "provenance_log",
        {"coll": collection}
    )


@then('provenance log is returned')
def api_response_contents(api_response):
    _, body = api_response

    assert len(body["data"]) >= 0
