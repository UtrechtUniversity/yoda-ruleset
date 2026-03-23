# coding=utf-8
"""Vault Retirement API feature tests."""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_vault_retire.feature')


@given(parsers.parse("data package exists in {vault}"), target_fixture="data_package")
def api_vault_data_package(user, vault):
    http_status, body = api_request(
        user,
        "browse_collections",
        {"coll": vault, "sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0

    return body["data"]["items"][0]["name"]


@given(parsers.parse("the Yoda vault request retirement API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_request_retirement(user, vault, data_package):
    return api_request(
        user,
        "vault_request_retirement",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault cancel retirement API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_cancel_retirement(user, vault, data_package):
    return api_request(
        user,
        "vault_cancel_retirement",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault approve retirement API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_approve_retirement(user, vault, data_package):
    return api_request(
        user,
        "vault_approve_retirement",
        {"coll": vault + "/" + data_package}
    )


@then(parsers.parse('data package in {vault} retirement status is "{status}"'))
def data_package_status(user, vault, data_package, status):
    for _i in range(36):
        _, body = api_request(
            user,
            "vault_collection_details",
            {"path": vault + "/" + data_package}
        )

        if body["data"]["retire"]["status"] == status:
            return True
        time.sleep(10)

    raise AssertionError()
