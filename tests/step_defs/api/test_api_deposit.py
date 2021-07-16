# coding=utf-8
"""Deposit API feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_deposit.feature')


@given('the Yoda deposit path API is queried', target_fixture="api_response")
def api_deposit_path(user):
    return api_request(
        user,
        "deposit_path",
        {}
    )


@given('the Yoda deposit status API is queried', target_fixture="api_response")
def api_deposit_status(user):
    return api_request(
        user,
        "deposit_status",
        {}
    )


@then('deposit path is returned')
def api_deposit_path_return(api_response):
    _, body = api_response

    assert body["data"]["deposit_path"]


@then('deposit status is returned')
def api_deposit_status_return(api_response):
    _, body = api_response

    assert not body["data"]["data"]
    assert not body["data"]["metadata"]
