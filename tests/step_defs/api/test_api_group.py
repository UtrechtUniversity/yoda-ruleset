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

scenarios('../../features/api/api_group.feature')


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
        "group_search_users",
        {"pattern": pattern}
    )


@given(parsers.parse('the group "{groupName}" does not exist'))
@then(parsers.parse('the group "{groupName}" no longer exists'))
def api_group_does_not_exist(user, groupName):
    _, body = api_request(
        user,
        "group_exists",
        {"groupName": groupName}
    )

    exists = body['data']
    assert not exists


@given(parsers.parse('the user creates a new group "{groupName}"'), target_fixture="api_response")
def api_group_create(user, groupName):
    return api_request(
        user,
        "group_create",
        {"groupName": groupName,
         "category": "abs",
         "subcategory": "cde",
         "description": "",
         "dataClassification": "wat"}
    )


@given(parsers.parse('the group "{groupName}" exists'))
def given_group_exists(user, groupName):
    _, body = api_request(
        user,
        "group_exists",
        {"groupName": groupName}
    )

    exists = body['data']
    assert exists


@given(parsers.parse('the user updates group "{groupName}"'), target_fixture="api_response")
def api_group_update(user, groupName):
    tobeDescription = 'To test or not to test, that is the question. Whether it is nobler in the mind to suffer the production errors and bugs of life, or to test and squash them all and by ending them hear "the button colour is wrong"...'

    return api_request(
        user,
        "group_update",
        {'groupName': groupName,
         'propertyName': 'description',
         'propertyValue': tobeDescription}
    )


@given(parsers.parse('the user deletes group "{groupName}"'), target_fixture="api_response")
def api_group_delete(user, groupName):
    return api_request(
        user,
        "group_delete",
        {"groupName": groupName}
    )


@given(parsers.parse('the user X "{newUser}" is not a member of group "{groupName}"'))
@then('user X is no longer a member of the group')
def given_user_is_not_member(user, newUser, groupName):
    _, body = api_request(
        user,
        "group_user_is_member",
        {"username": newUser,
         "groupName": groupName}
    )

    is_member = body["data"]
    assert not is_member


@given('the user adds user X to the group', target_fixture="api_response")
def api_group_create_user(user, newUser, groupName):
    return api_request(
        user,
        "group_user_add",
        {"username": newUser,
         "groupName": groupName}
    )


@given('the user updates the role of user X', target_fixture="api_response")
def api_group_update_user(user, newUser, groupName):
    return api_request(
        user,
        "group_user_update_role",
        {"username": newUser,
         "groupName": groupName,
         "newRole": "manager"}
    )


@given('the user removes user X from the group', target_fixture="api_response")
def api_group_delete_user(user, newUser, groupName):
    return api_request(
        user,
        "group_remove_user_from_group",
        {"username": newUser,
         "groupName": groupName}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then('the result is equal to "<users>"')
def then_users_found_match(api_response, users):
    _, body = api_response

    assert body["data"] == users.split(", ")


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


@then(parsers.parse('the group "{groupName}" is created'))
def then_group_created(user, groupName):
    _, body = api_request(
        user,
        'group_exists',
        {'groupName': groupName}
    )

    exists = body["data"]

    assert exists


@then(parsers.parse('the update to group "{groupName}" is persisted'))
def then_group_updated(user, groupName, api_response):
    _, body = api_request(
        user,
        "group_get_description",
        {"groupName": groupName}
    )

    description = body['data']
    tobeDescription = 'To test or not to test, that is the question. Whether it is nobler in the mind to suffer the production errors and bugs of life, or to test and squash them all and by ending them hear "the button colour is wrong"...'

    assert description == tobeDescription


@then('user X is now a member of the group')
@given(parsers.parse('the user X "{newUser}" is a member of group "{groupName}"'))
def then_user_is_member(user, newUser, groupName):
    _, body = api_request(
        user,
        "group_user_is_member",
        {"username": newUser,
         "groupName": groupName}
    )

    is_member = body['data']
    assert is_member


@then('the update is persisted')
def then_user_update_persisted(user, newUser, groupName):
    _, body = api_request(
        user,
        "group_get_user_role",
        {"username": newUser,
         "groupName": groupName}
    )

    role = body["data"]
    assert role == "manager"
