# coding=utf-8
"""Meta API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
from collections import OrderedDict
from urllib.parse import urlparse

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_meta.feature')


@given(parsers.parse("metadata JSON exists in {collection}"))
def api_meta_form_save(user, collection):
    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": collection}
    )

    path = urlparse(body['data']['schema']['$id']).path
    schema = path.split("/")[2]

    cwd = os.getcwd()
    with open("{}/files/{}.json".format(cwd, schema)) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    http_status, _ = api_request(
        user,
        "meta_form_save",
        {"coll": collection, "metadata": metadata}
    )

    assert http_status == 200


@given(parsers.parse("metadata JSON exists in {clone_collection}"))
def metadata_removed(user, clone_collection):
    http_status, body = api_request(
        user,
        "browse_folder",
        {"coll": clone_collection}
    )

    assert http_status == 200

    # Check if yoda-metadata.json is in browse results of collection.
    found = False
    for item in body['data']['items']:
        if item["name"] == "yoda-metadata.json":
            found = True

    assert found


@given(parsers.parse("subcollection {target_coll} exists"))
def subcollection_exists(user, target_coll):
    http_status, _ = api_request(
        user,
        "research_collection_details",
        {"path": target_coll}
    )

    if http_status == 400:
        x = target_coll.split('/')

        http_status, _ = api_request(
            user,
            "research_folder_add",
            {"coll": "/".join(x[:-1]), "new_folder_name": x[-1]}
        )

        assert http_status == 200
    else:
        assert True


@given(parsers.parse("the Yoda meta remove API is queried with metadata and {clone_collection}"), target_fixture="api_response")
def api_meta_remove(user, clone_collection):
    return api_request(
        user,
        "meta_remove",
        {"coll": clone_collection}
    )


@given(parsers.parse("the Yoda meta clone file API is queried with {target_coll}"), target_fixture="api_response")
def api_response(user, target_coll):
    return api_request(
        user,
        "meta_clone_file",
        {"target_coll": target_coll}
    )


@then(parsers.parse("metadata JSON is removed from {clone_collection}"))
def metadata_removed_collection(user, clone_collection):
    http_status, body = api_request(
        user,
        "browse_folder",
        {"coll": clone_collection}
    )

    assert http_status == 200

    # Check if yoda-metadata.json is in browse results of collection.
    found = True
    for item in body['data']['items']:
        if item["name"] == "yoda-metadata.json":
            found = False

    assert found


@then(parsers.parse("metadata JSON is cloned into {target_coll}"))
def metadata_cloned(user, target_coll):
    http_status, body = api_request(
        user,
        "meta_form_load",
        {"coll": target_coll}
    )

    assert http_status == 200
