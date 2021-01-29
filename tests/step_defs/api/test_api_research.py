# coding=utf-8
"""Research API feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request, post_form_data

scenarios('../../features/api/api_research.feature', '../../features/api/api_research_locked.feature')


@given('the Yoda research folder add API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_research_folder_add(user, folder, collection):
    return api_request(
        user,
        "research_folder_add",
        {"coll": collection, "new_folder_name": folder}
    )


@given('the Yoda research folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"', target_fixture="api_response")
def api_research_folder_rename(user, folder_old, folder, collection):
    return api_request(
        user,
        "research_folder_rename",
        {"new_folder_name": folder, "coll": collection, "org_folder_name": folder_old}
    )


@given('the Yoda research folder delete API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_research_folder_delete(user, folder, collection):
    return api_request(
        user,
        "research_folder_delete",
        {"coll": collection, "folder_name": folder}
    )


@given('the Yoda research file copy API is queried with "<file>", "<copy>" and "<collection>"', target_fixture="api_response")
def api_research_file_copy(user, file, copy, collection):
    return api_request(
        user,
        "research_file_copy",
        {"coll": collection, "file": file, "copy": copy}
    )


@given('the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"', target_fixture="api_response")
def api_research_file_rename(user, file, file_renamed, collection):
    return api_request(
        user,
        "research_file_rename",
        {"new_file_name": file_renamed, "coll": collection, "org_file_name": file}
    )


@given('a file "<file>" is uploaded in "<folder>"', target_fixture="api_response")
def api_research_file_upload(user, file, folder):
    return post_form_data(
        user,
        "research/browse/upload",
        {"file": (file, "test"), "filepath": (None, folder)}
    )


@given('the Yoda research file delete API is queried with "<file>" and "<collection>"', target_fixture="api_response")
def api_research_file_delete(user, file, collection):
    return api_request(
        user,
        "research_file_delete",
        {"coll": collection, "file_name": file}
    )


@given('the Yoda research system metadata API is queried with "<collection>"', target_fixture="api_response")
def api_research_system_metadata(user, collection):
    return api_request(
        user,
        "research_system_metadata",
        {"coll": collection}
    )


@given('the Yoda research collection details API is queried with "<collection>"', target_fixture="api_response")
def api_research_collection_details(user, collection):
    return api_request(
        user,
        "research_collection_details",
        {"path": collection}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code


def object_exists(user, object, collection):
    http_status, body = api_request(
        user,
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
def folder_exists(user, folder, collection):
    assert object_exists(user, folder, collection)


@then('folder "<folder>" does not exists in "<collection>"')
def folder_not_exists(user, folder, collection):
    assert not object_exists(user, folder, collection)


@then('file "<file>" exists in "<collection>"')
def file_exists(user, file, collection):
    assert object_exists(user, file, collection)


@then('file "<file>" does not exist in "<collection>"')
def file_not_exist(user, file, collection):
    assert not object_exists(user, file, collection)


@then('file "<copy>" exists in "<collection>"')
def file_copy_exists(user, copy, collection):
    assert object_exists(user, copy, collection)


@then('file "<copy>" does not exist in "<collection>"')
def file_copy_not_exist(user, copy, collection):
    assert not object_exists(user, copy, collection)


@then('folder "<copy>" does not exists in "<collection>"')
def folder_copy_not_exists(user, folder, collection):
    assert not object_exists(user, folder, collection)


@then('file "<file_renamed>" exists in "<collection>"')
def file_renamed_exists(user, file_renamed, collection):
    assert object_exists(user, file_renamed, collection)


@then('file "<file_renamed>" does not exist in "<collection>"')
def file_renamed_not_exist(user, file_renamed, collection):
    assert not object_exists(user, file_renamed, collection)
