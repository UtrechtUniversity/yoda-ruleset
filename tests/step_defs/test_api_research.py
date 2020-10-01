# coding=utf-8
"""Research API feature tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session>
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../features/api_research.feature')

@given('the Yoda research folder add API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder, collection):
    return api_request(
        "research_folder_add",
        {"coll": collection, "new_folder_name": folder}
    )

@given('the Yoda research folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder_old, folder, collection):
    return api_request(
        "research_folder_rename",
        {"new_folder_name": folder, "coll": collection, "org_folder_name": folder_old}
    )

@given('the Yoda research folder delete API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder, collection):
    return api_request(
        "research_folder_delete",
        {"coll": collection, "folder_name": folder}
    )

@given('the Yoda research file copy API is queried with "<file>", "<copy>" and "<collection>"', target_fixture="api_response")
def api_response(file, copy, collection):
    return api_request(
        "research_file_copy",
        {"coll": collection, "file": file, "copy": copy}
    )

@given('the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"', target_fixture="api_response")
def api_response(file, file_renamed, collection):
    return  api_request(
        "research_file_rename",
        {"new_file_name": file_renamed, "coll": collection, "org_file_name": file}
    )

@given('the Yoda research file delete API is queried with "<file>" and "<collection>"', target_fixture="api_response")
def api_response(file, collection):
    return  api_request(
        "research_file_delete",
        {"coll": collection, "file_name": file}
    )

@given('the Yoda research system metadata API is queried with "<collection>"', target_fixture="api_response")
def api_response(collection):
    return api_request(
        "research_system_metadata",
        {"coll": collection}
    )

@given('the Yoda research collection details API is queried with "<collection>"', target_fixture="api_response")
def api_response(collection):
    return api_request(
        "research_collection_details",
        {"path": collection}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code


def object_exists(object, collection):
    http_status, body = api_request(
        "browse_folder",
        {"coll": collection}
    )

    assert http_status == 200

    # Check if object exists in collection.
    found = False
    for item in body['data']['items']:
        if item["name"] == object:
            found = True

    return found

@then('folder "<folder>" exists in "<collection>"')
def api_response_contents(folder, collection):
    assert object_exists(folder, collection)

@then('folder "<folder>" does not exists in "<collection>"')
def api_response_contents(folder, collection):
    assert not object_exists(folder, collection)

@then('file "<file>" exists in "<collection>"')
def api_response_contents(file, collection):
    assert object_exists(file, collection)

@then('file "<copy>" exists in "<collection>"')
def api_response_contents(copy, collection):
    assert object_exists(copy, collection)

@then('file "<file_renamed>" exists in "<collection>"')
def api_response_contents(file_renamed, collection):
    assert object_exists(file_renamed, collection)

@then('file "<file>" does not exist in "<collection>"')
def api_response_contents(file, collection):
    assert not object_exists(file, collection)
