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


@given('the Yoda deposit create API is queried', target_fixture="api_response")
def api_deposit_path(user):
    return api_request(
        user,
        "deposit_create",
        {}
    )


@given('deposit exists', target_fixture="deposit_name")
def deposit_exists(user):
    http_status, body = api_request(
        user,
        "browse_collections",
        {"coll": "/tempZone/home/deposit-pilot"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0
    return body["data"]["items"][0]["name"]


@given('the Yoda deposit status API is queried', target_fixture="api_response")
def api_deposit_status(user, deposit_name):
    return api_request(
        user,
        "deposit_status",
        {"path": "/deposit-pilot/{}".format(deposit_name)}
    )


@given('the Yoda deposit submit API is queried', target_fixture="api_response")
def api_deposit_clear(user, deposit_name):
    return api_request(
        user,
        "deposit_submit",
        {"path": "/deposit-pilot/{}".format(deposit_name)}
    )


@then('deposit path is returned')
def api_deposit_path_return(api_response):
    _, body = api_response
    assert body["data"]["deposit_path"]


@then('deposit status is returned')
def api_deposit_status_return(api_response):
    _, body = api_response
    assert body["data"]
    assert not body["data"]["data"]
    assert not body["data"]["metadata"]
