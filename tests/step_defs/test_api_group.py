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


@given('the user searches for users matching "<pattern>"', target_fixture="api_response")
def api_group_search_users(user, pattern):
    return api_request(
        user,
        "tbd",
        {}
    )


@given(parsers.parse('the group "{groupName}" does not exist'))
def api_group_does_not_exist(user, groupName):
    assert False


@given('the user creates a new group "{groupName}"', target_fixture="api_response")
def api_group_create(user, groupName):
    return api_request(
        user,
        "tbd",
        { "args" : "" }
    )


@given(parsers.parse('the group "{groupName}" exists'))
def given_group_exists(user, groupName):
    assert False


@given('the user updates group "{groupName}"', target_fixture="api_response")
def api_group_update(user, groupName):
    return api_request(
        user,
        "tbd",
        {}
    )


@given('the user deletes group "{groupName}"', target_fixture="api_response")
def api_group_delete(user, groupName):
    return api_request(
        user,
        "tbd",
        {}
    )


@given(parsers.parse('there exists no user named "{newUser}"'))
def given_user_does_not_exist(user, newUser):
    assert False


@given('the user creates the new user', target_fixture="api_response")
def api_group_create_user(user, newUser):
    return api_request(
        user,
        "tbd",
        {}
    )


@given(parsers.parse('there exists a user X named "{targetUser}"'))
def given_target_user_exists(user, targetUser):
    assert False


@given('the user updates user X', target_fixture="api_response")
def api_group_update_user(user, targetUser):
    return api_request(
        user,
        "tbd",
        {}
    )


@given('the user deletes user X', target_fixture="api_response")
def api_group_delete_user(user, targetUser):
    return api_request(
        user,
        "tbd",
        {}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then('the result is equal to "<users>"')
def then_users_found_match(api_response, users):
    assert False


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


@then('the group "{groupName}" is created')
def then_group_created(api_response, groupName):
    assert False


@then('the update to group "{groupName}" is persisted')
def then_group_updated(user, groupNamer, api_response):
    assert False


@then('the group "{groupName}" no longer exists')
def then_group_does_not_exist(user, groupName):
    assert False


@then('the new user is persisted')
def then_user_exists(user, newUser):
    assert False


@then('the user update is persisted')
def then_user_update_persisted(user, targetUser):
    assert False


@then('the user no longer exists')
def  then_user_deleted(user, targetUser):
    assert False