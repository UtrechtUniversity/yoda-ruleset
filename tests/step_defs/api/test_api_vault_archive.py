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


@given(parsers.parse("the Yoda vault archive status API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_system_metadata(user, vault, data_package):
    return api_request(
        user,
        "vault_archival_status",
        {"coll": vault + "/" + data_package}
    )


@then(parsers.parse('data package in {vault} status is "{status}"'))
def data_package_status(user, vault, data_package, status):
    for _i in range(25):
        _, body = api_request(
            user,
            "vault_collection_details",
            {"path": vault + "/" + data_package}
        )

        if body["data"]["status"] == status:
            return True
        time.sleep(5)

    raise AssertionError()
