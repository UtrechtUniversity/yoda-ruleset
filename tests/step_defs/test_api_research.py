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

@given('the Yoda folder add API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder, collection):
    return api_request(
        "research_folder_add",
        {"coll": collection, "new_folder_name": folder}
    )

@given('the Yoda folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder_old, folder, collection):
    return api_request(
        "research_folder_rename",
        {"new_folder_name": folder, "coll": collection, "org_folder_name": folder_old}
    )

@given('the Yoda folder delete API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_response(folder, collection):
    return api_request(
        "research_folder_delete",
        {"coll": collection, "folder_name": folder}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code
    assert body == {"status": "ok", "status_info": None, "data": {"proc_status_info": "", "proc_status": "ok"}}


@then('folder "<folder>" exists in "<collection>"')
def api_response_contents(folder, collection):
    http_status, body = api_request(
        "browse_folder",
        {"coll": collection}
    )

    assert http_status == 200

    # Check if folder is in browse results of collection.
    found = False
    for item in body['data']['items']:
        if item["name"] == folder:
            found = True

    assert found

@then('folder "<folder>" does not exists in "<collection>"')
def api_response_contents(folder, collection):
    http_status, body = api_request(
        "browse_folder",
        {"coll": collection}
    )

    assert http_status == 200

    # Check if folder is not in browse results of collection.
    found = True
    for item in body['data']['items']:
        if item["name"] == folder:
            found = False

    assert found
