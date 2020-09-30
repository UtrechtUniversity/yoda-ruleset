# coding=utf-8
"""Folder feature tests."""

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../features/api_folder.feature')

@given('the Yoda folder lock API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_lock",
        {"coll": folder}
    )

@given('the Yoda folder get locks API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_get_locks",
        {"coll": folder}
    )

@given('the Yoda folder unlock API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_unlock",
        {"coll": folder}
    )

@given('the Yoda folder submit API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_submit",
        {"coll": folder}
    )

@given('the Yoda folder unsubmit API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_unsubmit",
        {"coll": folder}
    )

@given('the Yoda folder reject API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_reject",
        {"coll": folder}
    )

@given('the Yoda folder accept API is queried with "<folder>"', target_fixture="api_response")
def api_response(folder):
    return api_request(
        "folder_accept",
        {"coll": folder}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code

@then(parsers.parse('folder "<folder>" status is "{status}"'))
def folder_status(folder, status):
    # Status FOLDER is empty.
    if status == "FOLDER":
        status = ""

    _, body = api_request(
        "research_collection_details",
        {"path": folder}
    )

    assert body["data"]["status"] == status

@then('folder locks contains "<folder>"')
def folder_status(api_response, folder):
    _, body = api_response
    assert folder in body["data"]
