# coding=utf-8
"""Deposit API feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

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

from conftest import api_request, upload_data

scenarios('../../features/api/api_deposit_open.feature', '../../features/api/api_deposit_restricted.feature')


@given('the Yoda deposit create API is queried', target_fixture="api_response")
def api_deposit_path(user):
    return api_request(
        user,
        "deposit_create",
        {}
    )


@given('deposit exists', target_fixture="deposit_name")
def deposit_exists(user):
    http_status, body = api_request(
        user,
        "browse_collections",
        {"coll": "/tempZone/home/deposit-pilot", "sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0
    return body["data"]["items"][0]["name"]


@given('deposit is archived')
def deposit_is_archived(user):
    time.sleep(12)


@given('the Yoda deposit status API is queried', target_fixture="api_response")
def api_deposit_status(user, deposit_name):
    return api_request(
        user,
        "deposit_status",
        {"path": "/deposit-pilot/{}".format(deposit_name)}
    )


@given('the Yoda deposit submit API is queried', target_fixture="api_response")
def api_deposit_clear(user, deposit_name):
    return api_request(
        user,
        "deposit_submit",
        {"path": "/deposit-pilot/{}".format(deposit_name)}
    )


@given(parsers.parse("a file {file} is uploaded in deposit"), target_fixture="api_response")
def api_deposit_file_upload(user, file, deposit_name):
    return upload_data(
        user,
        file,
        "/deposit-pilot/{}".format(deposit_name)
    )


@given('metadata JSON is created in deposit', target_fixture="api_response")
def api_response(user, deposit_name):
    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name)}
    )

    path = urlparse(body['data']['schema']['$id']).path
    schema = path.split("/")[2]

    cwd = os.getcwd()
    with open("{}/files/{}.json".format(cwd, schema)) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    return api_request(
        user,
        "meta_form_save",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name), "metadata": metadata}
    )


@given('data access restriction is open')
def data_access_restriction_open(user, deposit_name):
    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name)}
    )

    metadata = body['data']['metadata']
    metadata['Data_Access_Restriction'] = "Open - freely retrievable"

    return api_request(
        user,
        "meta_form_save",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name), "metadata": metadata}
    )


@given('data access restriction is restricted')
def data_access_restriction_restricted(user, deposit_name):
    _, body = api_request(
        user,
        "meta_form_load",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name)}
    )

    metadata = body['data']['metadata']
    metadata['Data_Access_Restriction'] = "Restricted - available upon request"

    return api_request(
        user,
        "meta_form_save",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name), "metadata": metadata}
    )


@given(parsers.parse("the Yoda browse collections API is queried with {collection}"), target_fixture="api_response")
def api_browse_collections(user, collection):
    return api_request(
        user,
        "browse_collections",
        {"coll": collection, "sort_order": "desc"}
    )


@then('deposit path is returned')
def api_deposit_path_return(api_response):
    _, body = api_response
    assert body["data"]["deposit_path"]


@then('deposit status is returned')
def api_deposit_status_return(api_response):
    _, body = api_response
    assert body["data"]
    assert body["data"]["data"]
    assert body["data"]["metadata"]


@then('the browse result contains deposit')
def api_response_contains(api_response, deposit_name):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check if expected result is in browse results.
    found = False
    for item in body['data']['items']:
        if item["name"].startswith(deposit_name):
            found = True

    assert found


@then('the browse result does not contain deposit')
def api_response_not_contain(api_response, deposit_name):
    _, body = api_response

    # Check if expected result is in browse results.
    found = True
    for item in body['data']['items']:
        if deposit_name in item["name"]:
            found = False

    assert found
