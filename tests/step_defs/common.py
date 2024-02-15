#!/usr/bin/env python3
"""Common test functions."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers
)

from conftest import api_request


@given(parsers.parse("collection {collection} exists"))
def collection_exists(user, collection):
    http_status, _ = api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )
    assert http_status == 200


@given(parsers.parse("{collection} is unlocked"))
def collection_is_unlocked(user, collection):
    _, body = api_request(
        user,
        "research_collection_details",
        {"path": collection}
    )

    if body["data"]["status"] == "LOCKED":
        http_status, _ = api_request(
            user,
            "folder_unlock",
            {"coll": collection}
        )
        assert http_status == 200
    else:
        assert body["data"]["status"] == "" or body["data"]["status"] == "SECURED"


@given(parsers.parse("{collection} is locked"))
def collection_is_locked(user, collection):
    _, body = api_request(
        user,
        "research_collection_details",
        {"path": collection}
    )

    if body["data"]["status"] != "LOCKED":
        http_status, _ = api_request(
            user,
            "folder_lock",
            {"coll": collection}
        )
        assert http_status == 200
    else:
        assert body["data"]["status"] == "LOCKED"
