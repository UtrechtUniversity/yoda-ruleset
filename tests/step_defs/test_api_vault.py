# coding=utf-8
"""Vault API feature tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session>
"""

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../features/api_vault.feature')

@given('data package exists in "<vault>"', target_fixture="data_package")
def data_package(vault):
    http_status, body = api_request(
        "browse_collections",
        {"coll": vault, "sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0

    return body["data"]["items"][0]["name"]

@given('the Yoda vault submit API is queried on datapackage in "<vault>"', target_fixture="api_response")
def api_response(vault, data_package):
    return api_request(
        "vault_submit",
        {"coll": vault + "/" + data_package}
    )

@given('the Yoda vault cancel API is queried on datapackage in "<vault>"', target_fixture="api_response")
def api_response(vault, data_package):
    return api_request(
        "vault_cancel",
        {"coll": vault + "/" + data_package}
    )

@given('the Yoda vault approve API is queried on datapackage in "<vault>"', target_fixture="api_response")
def api_response(vault, data_package):
    return api_request(
        "vault_approve",
        {"coll": vault + "/" + data_package}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code

@then(parsers.parse('data package status is "{status}"'))
def data_package_status(vault, data_package, status):
    _, body = api_request(
        "vault_collection_details",
        {"path": vault + "/" + data_package}
    )

    assert body["data"]["status"] == status

@then('folder locks contains "<folder>"')
def folder_status(api_response, folder):
    _, body = api_response
    assert folder in body["data"]
