# coding=utf-8
"""Group API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../features/api_group.feature')


@given('the Yoda group data API is queried', target_fixture="api_response")
def api_group_data(user):
    return api_request(
        user,
        "group_data",
        {}
    )


@given('the Yoda group data filtered API is queried with "<user>" and "<zone>"', target_fixture="api_response")
def api_group_data_filtered(user, zone):
    return api_request(
        user,
        "group_data_filtered",
        {"user_name": user, "zone_name": zone}
    )


@given('the Yoda group categories API is queried', target_fixture="api_response")
def api_group_categories(user):
    return api_request(
        user,
        "group_categories",
        {}
    )


@given('the Yoda group subcategories API is queried with "<category>"', target_fixture="api_response")
def api_group_subcategories(user, category):
    return api_request(
        user,
        "group_subcategories",
        {"category": category}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then('group "<group>" exists')
def group_exists(api_response, group):
    _, body = api_response

    assert len(body['data']) > 0

    # Check if expected result is in group results.
    found = False
    for group_data in body['data']:
        if group_data['name'] == group:
            found = True
            break

    assert found


@then('category "<category>" exists')
def category_exists(api_response, category):
    _, body = api_response

    assert len(body['data']) > 0

    # Check if expected result is in group categories results.
    found = False
    for category_name in body['data']:
        if category_name == category:
            found = True
            break

    assert found
