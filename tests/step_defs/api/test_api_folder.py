# coding=utf-8
"""Folder API feature tests."""

import json
import os
import time
from collections import OrderedDict
from urllib.parse import urlparse

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_folder.feature')


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
    with open("{}/files/{}.json".format(cwd, schema)) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    http_status, _ = api_request(
        user,
        "meta_form_save",
        {"coll": folder, "metadata": metadata}
    )

    assert http_status == 200


@then(parsers.parse("folder {folder} status is {status}"))
def folder_status(user, folder, status):
    # Status FOLDER is empty.
    if status == "FOLDER":
        status = ""

    for _i in range(25):
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
    assert "/{}".format(x[-1]) in body["data"]
