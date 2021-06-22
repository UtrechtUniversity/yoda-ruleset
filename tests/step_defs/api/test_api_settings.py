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


@given('the Yoda settings save API is queried with "<attribute>" and "<value>"', target_fixture="api_response")
def api_settings_save(user, attribute, value):
    settings = {attribute: value}
    return api_request(
        user,
        "settings_save",
        {"settings": settings}
    )


@given('the Yoda settings load API is queried', target_fixture="api_response")
def api_settings_load(user):
    return api_request(
        user,
        "settings_load",
        {}
    )


@then('"<attribute>" contains "<value>"')
def api_attribute_value(api_response, attribute, value):
    _, body = api_response
    assert body["data"][attribute] == value
