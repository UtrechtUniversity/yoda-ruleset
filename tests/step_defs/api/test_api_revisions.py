# coding=utf-8
"""Revisions API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_revisions.feature')


@given(parsers.parse("the Yoda revision search API is queried with {filename}"), target_fixture="api_response")
def api_search_revisions_on_filename(user, filename):
    return api_request(
        user,
        "revisions_search_on_filename",
        {"searchString": filename, "offset": 0, "limit": "10"}
    )


@then(parsers.parse("{revision_search_result} is found"))
def api_response_revision_search_result(api_response, revision_search_result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check expected result is in reveived search results.
    found = False
    for item in body['data']['items']:
        if revision_search_result in item["main_original_dataname"]:
            found = True
            break

    assert found


@given(parsers.parse("the Yoda revision list API is queried with {path}"), target_fixture="api_response")
def api_get_revision_list(user, path):
    return api_request(
        user,
        "revisions_list",
        {"path": path}
    )


@then('revisions list is found')
def api_response_list_found(api_response):
    _, body = api_response

    for key in ['org_original_path', 'data_id', 'org_original_data_name', 'org_original_data_owner_name', 'dezoned_coll_name', 'org_original_group_name', 'org_original_coll_id', 'org_original_data_id', 'org_original_filesize', 'org_original_modify_time']:
        assert body['data']['revisions'][0][key]


@given(parsers.parse("the Yoda revision API is requested for first revision for {path}"), target_fixture="revision_id")
def api_get_first_revision_id_for_path(user, path):
    api_response = api_request(
        user,
        "revisions_list",
        {"path": path}
    )
    _, body = api_response
    assert body['data']['revisions'][0]['data_id']

    return body['data']['revisions'][0]['data_id']


@given(parsers.parse("the Yoda revision API is requested to restore revision in collection {coll_target} with name {new_filename} with revision id"), target_fixture="api_response")
def api_restore_revision(user, revision_id, coll_target, new_filename):
    return api_request(
        user,
        "revisions_restore",
        {"revision_id": revision_id, "overwrite": "restore_overwrite", "coll_target": coll_target, "new_filename": new_filename}
    )


@then('revision is restored successfully')
def api_response_revision_successfully_restored(api_response):
    http_status, _ = api_response

    assert http_status == 200
