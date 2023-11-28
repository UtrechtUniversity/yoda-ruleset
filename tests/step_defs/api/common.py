#!/usr/bin/env python3
"""Common API test functions."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
from collections import OrderedDict
from urllib.parse import urlparse

from pytest_bdd import (
    given,
    parsers,
    then
)

from conftest import api_request


@given(parsers.parse("the Yoda browse folder API is queried with {collection}"), target_fixture="api_response")
def api_browse_folder(user, collection):
    return api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )


@then(parsers.parse("the browse result contains {result}"))
def api_response_contains(api_response, result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check if expected result is in browse results.
    found = False
    for item in body['data']['items']:
        if item["name"] == result:
            found = True

    assert found


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


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


@given(parsers.parse("the Yoda meta form load API is queried with {collection}"), target_fixture="api_response")
def api_meta_form_load(user, collection):
    return api_request(
        user,
        "meta_form_load",
        {"coll": collection}
    )


@then(parsers.parse("metadata is returned for {collection}"))
def metadata_returned(api_response, collection):
    http_status, body = api_response

    assert http_status == 200
