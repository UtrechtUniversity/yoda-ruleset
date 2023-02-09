# coding=utf-8
"""Vault Archive API feature tests."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_vault_archive.feature')


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


@given(parsers.parse("the Yoda vault archival status API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_archival_status(user, vault, data_package):
    return api_request(
        user,
        "vault_archival_status",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault archive API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_archive(user, vault, data_package):
    return api_request(
        user,
        "vault_archive",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault extract API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_extract(user, vault, data_package):
    return api_request(
        user,
        "vault_extract",
        {"coll": vault + "/" + data_package}
    )


@then(parsers.parse('the data package in {vault} is archivable'))
def data_package_archivable(user, vault, data_package):
    _, body = api_request(
        user,
        "vault_collection_details",
        {"path": vault + "/" + data_package}
    )

    return body["data"]["archive"]["archivable"]


@then(parsers.parse('data package in {vault} archival status is "{status}"'))
def data_package_archival_status(user, vault, data_package, status):
    for _i in range(36):
        _, body = api_request(
            user,
            "vault_collection_details",
            {"path": vault + "/" + data_package}
        )

        if body["data"]["archive"]["status"] == status:
            return True
        time.sleep(10)

    raise AssertionError()
