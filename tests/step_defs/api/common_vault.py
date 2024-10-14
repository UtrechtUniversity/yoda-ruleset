# coding=utf-8
"""Vault API feature tests."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from collections import OrderedDict
from urllib.parse import urlparse

from pytest_bdd import (
    given,
    parsers,
    then
)

from conftest import api_request


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


@given(parsers.parse("the Yoda vault submit API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_submit(user, vault, data_package):
    return api_request(
        user,
        "vault_submit",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault cancel API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_cancel(user, vault, data_package):
    return api_request(
        user,
        "vault_cancel",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault approve API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_approve(user, vault, data_package):
    return api_request(
        user,
        "vault_approve",
        {"coll": vault + "/" + data_package}
    )


@given('the Yoda vault preservable formats lists API is queried', target_fixture="api_response")
def api_vault_preservable_formats_lists(user):
    return api_request(
        user,
        "vault_preservable_formats_lists",
        {}
    )


@given(parsers.parse("the Yoda vault unpreservable files API is queried with {list} on datapackage in {vault}"), target_fixture="api_response")
def api_vault_unpreservable_files(user, list, vault, data_package):
    return api_request(
        user,
        "vault_unpreservable_files",
        {"coll": vault + "/" + data_package, "list_name": list}
    )


@given(parsers.parse("the Yoda vault system metadata API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_system_metadata(user, vault, data_package):
    return api_request(
        user,
        "vault_system_metadata",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault collection details API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_vault_collection_details(user, vault, data_package):
    return api_request(
        user,
        "vault_collection_details",
        {"path": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault revoke read access research group API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_revoke_read_access_research_group(user, vault, data_package):
    return api_request(
        user,
        "revoke_read_access_research_group",
        {"coll": vault + "/" + data_package}
    )


@given(parsers.parse("the Yoda vault grant read access research group API is queried on datapackage in {vault}"), target_fixture="api_response")
def api_grant_read_access_research_group(user, vault, data_package):
    return api_request(
        user,
        "grant_read_access_research_group",
        {"coll": vault + "/" + data_package}
    )


@given('the Yoda vault get publication terms API is queried', target_fixture="api_response")
def api_vault_get_publication_terms(user):
    return api_request(
        user,
        "vault_get_publication_terms",
        {}
    )


@given(parsers.parse('the Yoda vault get published packages API is queried with {vault}'), target_fixture="api_response")
def api_vault_get_published_packages(user, vault):
    return api_request(
        user,
        "vault_get_published_packages",
        {"path": vault}
    )


@given(parsers.parse("the Yoda meta form save API is queried with metadata on datapackage in {vault}"), target_fixture="api_response")
def api_meta_form_save_vault(user, vault, data_package):

    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": vault + "/" + data_package}
    )

    path = urlparse(body['data']['schema']['$id']).path
    schema = path.split("/")[2]

    cwd = os.getcwd()
    with open("{}/files/{}.json".format(cwd, schema), encoding="utf8") as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    # Change metadata title.
    metadata["Title"] = "{} - update".format(metadata["Title"])

    return api_request(
        user,
        "meta_form_save",
        {"coll": vault + "/" + data_package, "metadata": metadata}
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


@then(parsers.parse('data package in {vault} passes troubleshooting script checks'))
def api_vault_batch_troubleshoot(user, vault, data_package):
    http_status, result = api_request(
        user,
        "batch_troubleshoot_published_data_packages",
        {"requested_package": data_package, "log_file": True, "offline": True}
    )
    assert http_status == 200
    data = result['data']
    assert len(data) == 1
    # Confirm that all checks passed for this data package
    for checks in data.values():
        assert all(checks.values())


@then('preservable formats lists are returned')
def preservable_formats_lists(api_response):
    http_status, body = api_response
    assert http_status == 200
    assert len(body["data"]) > 0


@then('unpreservable files are returned')
def unpreservable_files(api_response):
    http_status, body = api_response
    assert http_status == 200
    assert len(body["data"]) >= 0


@then('system metadata is returned')
def system_metadata(api_response):
    http_status, body = api_response
    assert http_status == 200
    assert len(body["data"]) >= 0
    assert "Data Package Size" in body["data"]


@then('publication terms are returned')
def publication_terms(api_response):
    http_status, body = api_response
    assert http_status == 200
    assert len(body["data"]) > 0


@then('published packages are returned')
def published_packages(api_response):
    http_status, body = api_response
    assert http_status == 200
    assert len(body["data"]) > 0
