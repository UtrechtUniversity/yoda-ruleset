# coding=utf-8
"""Research API feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    # parsers,
    scenarios,
    then,
)

from conftest import api_request, upload_data

# Tests for unlocked and locked research folders
scenarios('../../features/api/api_research.feature', '../../features/api/api_research_locked.feature')


@given('the Yoda research folder add API is queried with "<folder>" and "<collection>"', target_fixture="api_response")
def api_research_folder_add(user, folder, collection):
    return api_request(
        user,
        "research_folder_add",
        {"coll": collection, "new_folder_name": folder}
    )


@given('the Yoda research folder copy API is queried with "<folder>", "<copy>", and "<collection>"', target_fixture="api_response")
def api_research_folder_copy(user, folder, copy, collection):
    return api_request(
        user,
        "research_folder_copy",
        {"folder_path": collection + "/" + folder, "new_folder_path": collection + "/" + copy}
    )


@given('the Yoda research folder move API is queried with "<folder>", "<move>", and "<collection>"', target_fixture="api_response")
def api_research_folder_move(user, folder, move, collection):
    return api_request(
        user,
        "research_folder_move",
        {"folder_path": collection + "/" + folder, "new_folder_path": collection + "/" + move}
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


@given('the Yoda research file copy API is queried with "<file>", "<copy>", "<copy_collection>" and "<collection>"', target_fixture="api_response")
def api_research_file_copy(user, file, copy, copy_collection, collection):
    return api_request(
        user,
        "research_file_copy",
        {"filepath": collection + "/" + file, "new_filepath": copy_collection + "/" + copy}
    )


@given('the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"', target_fixture="api_response")
def api_research_file_rename(user, file, file_renamed, collection):
    return api_request(
        user,
        "research_file_rename",
        {"new_file_name": file_renamed, "coll": collection, "org_file_name": file}
    )


@given('the Yoda research file move API is queried with "<file>", "<move_collection>" and "<collection>"', target_fixture="api_response")
def api_research_file_move(user, file, move_collection, collection):
    return api_request(
        user,
        "research_file_move",
        {"filepath": collection + "/" + file, "new_filepath": move_collection + "/" + file}
    )


@given('a file "<file>" is uploaded in "<folder>"', target_fixture="api_response")
def api_research_file_upload(user, file, folder):
    return upload_data(
        user,
        file,
        folder
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


@then('file "<copy>" exists in "<copy_collection>"')
def file_copy_exists(user, copy, copy_collection):
    assert object_exists(user, copy, copy_collection)


@then('file "<copy>" does not exist in "<collection>"')
def file_copy_not_exist(user, copy, collection):
    assert not object_exists(user, copy, collection)


@then('folder "<copy>" exists in "<collection>"')
def folder_copy_exists(user, copy, collection):
    assert object_exists(user, copy, collection)


@then('folder "<move>" exists in "<collection>"')
def folder_move_exists(user, move, collection):
    assert object_exists(user, move, collection)


@then('folder "<folder>" does not exist in "<collection>"')
def folder_not_exist(user, folder, collection):
    assert not object_exists(user, folder, collection)


@then('folder "<folder_old>" does not exist in "<collection>"')
def folder_old_not_exist(user, folder_old, collection):
    assert not object_exists(user, folder_old, collection)


@then('file "<file_renamed>" exists in "<collection>"')
def file_renamed_exists(user, file_renamed, collection):
    assert object_exists(user, file_renamed, collection)


@then('file "<file_renamed>" does not exist in "<collection>"')
def file_renamed_not_exist(user, file_renamed, collection):
    assert not object_exists(user, file_renamed, collection)


@then('file "<file>" exists in "<move_collection>"')
def file_move_exists(user, file, move_collection):
    assert object_exists(user, file, move_collection)
