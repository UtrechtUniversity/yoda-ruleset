# coding=utf-8
"""Notifications API feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    scenarios,
)

from conftest import api_request

scenarios('../../features/api/api_notifications.feature')


@given('the Yoda notifications load API is queried with sort order "<sort_order>"', target_fixture="api_response")
def api_notifications_load(user, sort_order):
    return api_request(
        user,
        "notifications_load",
        {"sort_order": sort_order}
    )


@given('the Yoda notifications dismiss all API is queried', target_fixture="api_response")
def api_notifications_dismiss_all(user):
    return api_request(
        user,
        "notifications_dismiss_all",
        {}
    )
