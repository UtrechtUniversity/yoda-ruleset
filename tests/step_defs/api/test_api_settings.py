# coding=utf-8
"""Settings API feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_settings.feature')


@given('the Yoda settings save API is queried', target_fixture="api_response")
def api_settings_save(user):
    return api_request(
        user,
        "settings_save",
        {}
    )


@given('the Yoda settings load API is queried', target_fixture="api_response")
def api_settings_load(user):
    return api_request(
        user,
        "settings_load",
        {}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code
