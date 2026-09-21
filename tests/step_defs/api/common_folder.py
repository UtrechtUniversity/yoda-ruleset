# coding=utf-8
"""Common API folder feature tests."""

__copyright__ = 'Copyright (c) 2020-2026, Utrecht University'
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


@given(parsers.parse("the Yoda folder lock API is queried with {folder}"), target_fixture="api_response")
def api_folder_lock(user, folder):
    return api_request(
        user,
        "folder_lock",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder get locks API is queried with {folder}"), target_fixture="api_response")
def api_folder_get_locks(user, folder):
    return api_request(
        user,
        "folder_get_locks",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder unlock API is queried with {folder}"), target_fixture="api_response")
def api_folder_unlock(user, folder):
    return api_request(
        user,
        "folder_unlock",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder submit API is queried with {folder}"), target_fixture="api_response")
def api_folder_submit(user, folder):
    return api_request(
        user,
        "folder_submit",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder submit API is queried with {folder} and {delete_research_copy}"), target_fixture="api_response")
def api_folder_submit_move(user, folder, delete_research_copy="False"):
    return api_request(
        user,
        "folder_submit",
        {"coll": folder, "delete_research_copy": delete_research_copy.lower() == "true"}
    )


@given(parsers.parse("the Yoda folder unsubmit API is queried with {folder}"), target_fixture="api_response")
def api_folder_unsubmit(user, folder):
    return api_request(
        user,
        "folder_unsubmit",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder reject API is queried with {folder}"), target_fixture="api_response")
def api_folder_reject(user, folder):
    return api_request(
        user,
        "folder_reject",
        {"coll": folder}
    )


@given(parsers.parse("the Yoda folder accept API is queried with {folder}"), target_fixture="api_response")
def api_folder_accept(user, folder):
    return api_request(
        user,
        "folder_accept",
        {"coll": folder}
    )


@given(parsers.parse("metadata JSON exists in {folder}"))
def api_response(user, folder):
    api_request(
        user,
        "research_file_delete",
        {"coll": folder, "file_name": "yoda-metadata.json"}
    )

    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": folder}
    )

    path = urlparse(body['data']['schema']['$id']).path
    schema = path.split("/")[2]

    cwd = os.getcwd()
    with open(f"{cwd}/files/{schema}.json", encoding="utf8") as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    http_status, _ = api_request(
        user,
        "meta_form_save",
        {"coll": folder, "metadata": metadata}
    )

    assert http_status == 200


@given(parsers.parse("user creates a new folder {folder}"), target_fixture="api_response")
def api_research_folder_add(user, folder):
    parent_folder, new_folder_name = os.path.split(folder.rstrip('/'))

    return api_request(
        user,
        "research_folder_add",
        {
            "coll":            parent_folder,
            "new_folder_name": new_folder_name
        }
    )


@then(parsers.parse("folder {folder} status is {status}"))
def folder_status(user, folder, status):
    # Status FOLDER is empty.
    if status == "FOLDER":
        status = ""

    for _i in range(30):
        _, body = api_request(
            user,
            "research_collection_details",
            {"path": folder}
        )

        if body["data"]["status"] == status:
            return True
        time.sleep(5)

    raise AssertionError()


@then(parsers.parse("folder locks contains {folder}"))
def folder_locks(api_response, folder):
    _, body = api_response
    x = folder.split('/')
    assert f"/{x[-1]}" in body["data"]


@then(parsers.parse("folder {folder} does not exist"))
def folder_does_not_exist(user, folder):
    parent_folder, target = os.path.split(folder.rstrip('/'))

    for _ in range(30):
        _, body = api_request(
            user,
            "browse_folder",
            {"coll": parent_folder, "limit": 50}
        )

        items = body["data"].get("items")
        if not any(entry.get("name") == target for entry in items):
            return True

        time.sleep(5)

    raise AssertionError(f"Folder {folder} still exists after timeout")
