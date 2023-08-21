# coding=utf-8
"""Settings API feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request, api_request_get

scenarios('../../features/api/api_ping.feature')


@given('the Yoda ping API is queried', target_fixture="api_response")
def api_ping(user):
    return api_request(
        user,
        "ping",
        {}
    )


@then("response has valid sessions")
def api_ping_response_correct(api_response):
    _, body = api_response
    assert body ==   {'validity flask session': True, 'validity irods session': True}


@given('the Yoda ping API is queried without user', target_fixture="api_response")
def api_ping_without_user():
    return api_request_get(
        "ping"
    )


@then("response has no valid sessions")
def api_ping_response_correct(api_response):
    _, body = api_response
    assert body ==   {'validity flask session': False, 'validity irods session': False}
