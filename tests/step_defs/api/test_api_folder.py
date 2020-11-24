# coding=utf-8
"""Folder API feature tests."""

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_folder.feature')


@given('the Yoda folder lock API is queried with "<folder>"', target_fixture="api_response")
def api_folder_lock(user, folder):
    return api_request(
        user,
        "folder_lock",
        {"coll": folder}
    )


@given('the Yoda folder get locks API is queried with "<folder>"', target_fixture="api_response")
def api_folder_get_locks(user, folder):
    return api_request(
        user,
        "folder_get_locks",
        {"coll": folder}
    )


@given('the Yoda folder unlock API is queried with "<folder>"', target_fixture="api_response")
def api_folder_unlock(user, folder):
    return api_request(
        user,
        "folder_unlock",
        {"coll": folder}
    )


@given('the Yoda folder submit API is queried with "<folder>"', target_fixture="api_response")
def api_folder_submit(user, folder):
    return api_request(
        user,
        "folder_submit",
        {"coll": folder}
    )


@given('the Yoda folder unsubmit API is queried with "<folder>"', target_fixture="api_response")
def api_folder_unsubmit(user, folder):
    return api_request(
        user,
        "folder_unsubmit",
        {"coll": folder}
    )


@given('the Yoda folder reject API is queried with "<folder>"', target_fixture="api_response")
def api_folder_reject(user, folder):
    return api_request(
        user,
        "folder_reject",
        {"coll": folder}
    )


@given('the Yoda folder accept API is queried with "<folder>"', target_fixture="api_response")
def api_folder_accept(user, folder):
    return api_request(
        user,
        "folder_accept",
        {"coll": folder}
    )


@given('metadata JSON exists in "<folder>"')
def api_response(user, folder):
    http_status, _ = api_request(
        user,
        "meta_form_save",
        {"coll": folder,
         "metadata": {
             "links": [{
                 "rel": "describedby",
                 "href": "https://yoda.uu.nl/schemas/default-1/metadata.json"
             }],
             "Language": "en - English",
             "Retention_Period": 10,
             "Creator": [{
                 "Name": {
                     "Given_Name": "Test",
                     "Family_Name": "Test"
                 },
                 "Affiliation": ["Utrecht University"],
                 "Person_Identifier": [{}]
             }],
             "Data_Access_Restriction": "Restricted - available upon request",
             "Version": "0",
             "Title": "Test",
             "Description": "Test",
             "Data_Type": "Dataset",
             "Data_Classification": "Public",
             "License": "Creative Commons Attribution 4.0 International Public License"
         }}
    )

    assert http_status == 200


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then(parsers.parse('folder "<folder>" status is "{status}"'))
def folder_status(user, folder, status):
    # Status FOLDER is empty.
    if status == "FOLDER":
        status = ""

    _, body = api_request(
        user,
        "research_collection_details",
        {"path": folder}
    )

    assert body["data"]["status"] == status


@then('folder locks contains "<folder>"')
def folder_locks(api_response, folder):
    _, body = api_response
    assert folder in body["data"]
