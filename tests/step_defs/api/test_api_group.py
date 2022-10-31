# coding=utf-8
"""Group API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
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


@given('the Yoda group categories API is queried', target_fixture="api_response")
def api_group_categories(user):
    return api_request(
        user,
        "group_categories",
        {}
    )


@given(parsers.parse("the Yoda group subcategories API is queried with {category}"), target_fixture="api_response")
def api_group_subcategories(user, category):
    return api_request(
        user,
        "group_subcategories",
        {"category": category}
    )


@given(parsers.parse("the user searches for users matching {pattern}"), target_fixture="api_response")
def api_group_search_users(user, pattern):
    return api_request(
        user,
        "group_search_users",
        {"pattern": pattern}
    )


@given(parsers.parse('the group "{group_name}" does not exist'))
@then(parsers.parse('the group "{group_name}" no longer exists'))
def api_group_does_not_exist(user, group_name):
    _, body = api_request(
        user,
        "group_exists",
        {"group_name": group_name}
    )

    exists = body['data']
    assert not exists


@given(parsers.parse('the user creates a new group "{group_name}"'), target_fixture="api_response")
def api_group_create(user, group_name):
    return api_request(
        user,
        "group_create",
        {"group_name": group_name,
         "category": "api-test",
         "subcategory": "api-test",
         "schema_id": "default-2",
         "description": "",
         "data_classification": "public"}
    )


@given(parsers.parse('the group "{group_name}" exists'))
def given_group_exists(user, group_name):
    _, body = api_request(
        user,
        "group_exists",
        {"group_name": group_name}
    )

    exists = body['data']
    assert exists


@given(parsers.parse('the user updates group "{group_name}"'), target_fixture="api_response")
def api_group_update(user, group_name):
    tobeDescription = 'To test or not to test, that is the question. Whether it is nobler in the mind to suffer the production errors and bugs of life, or to test and squash them all and by ending them hear "the button colour is wrong"...'

    return api_request(
        user,
        "group_update",
        {'group_name': group_name,
         'property_name': 'description',
         'property_value': tobeDescription}
    )


@given(parsers.parse('the user deletes group "{group_name}"'), target_fixture="api_response")
def api_group_delete(user, group_name):
    return api_request(
        user,
        "group_delete",
        {"group_name": group_name}
    )


@given(parsers.parse('the user "{new_user}" is not a member of group "{group_name}"'))
@then(parsers.parse('user "{new_user}" is no longer a member of the group "{group_name}"'))
def given_user_is_not_member(user, new_user, group_name):
    _, body = api_request(
        user,
        "group_user_is_member",
        {"username": new_user,
         "group_name": group_name}
    )

    is_member = body["data"]
    assert not is_member


@given(parsers.parse('the user adds user "{new_user}" to the group "{group_name}"'), target_fixture="api_response")
def api_group_create_user(user, new_user, group_name):
    return api_request(
        user,
        "group_user_add",
        {"username": new_user,
         "group_name": group_name}
    )


@given(parsers.parse('the user updates the role of user "{new_user}" in group "{group_name}"'), target_fixture="api_response")
def api_group_update_user(user, new_user, group_name):
    return api_request(
        user,
        "group_user_update_role",
        {"username": new_user,
         "group_name": group_name,
         "new_role": "manager"}
    )


@given(parsers.parse('the user removes user "{new_user}" from the group "{group_name}"'), target_fixture="api_response")
def api_group_delete_user(user, new_user, group_name):
    return api_request(
        user,
        "group_remove_user_from_group",
        {"username": new_user,
         "group_name": group_name}
    )


@then(parsers.parse("the result is equal to {users}"))
def then_users_found_match(api_response, users):
    _, body = api_response

    users = users.split(", ")
    users.sort()
    assert body["data"] == users


@then(parsers.parse("group {group} exists"))
def group_exists(api_response, group):
    _, body = api_response

    assert len(body['data']['group_hierarchy']) > 0
    hierarchy = body['data']['group_hierarchy']

    # Check if expected result is in group hierarchy.
    found = False
    for category in hierarchy:
        for subcategory in hierarchy[category]:
            for group_name in hierarchy[category][subcategory]:
                if group_name == group:
                    found = True
                    break

    assert found


@then(parsers.parse("category {category} exists"))
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


@then(parsers.parse('the group "{group_name}" is created'))
def then_group_created(user, group_name):
    _, body = api_request(
        user,
        'group_exists',
        {'group_name': group_name}
    )

    exists = body["data"]

    assert exists


@then(parsers.parse('the update to group "{group_name}" is persisted'))
def then_group_updated(user, group_name, api_response):
    _, body = api_request(
        user,
        "group_get_description",
        {"group_name": group_name}
    )

    description = body['data']
    tobeDescription = 'To test or not to test, that is the question. Whether it is nobler in the mind to suffer the production errors and bugs of life, or to test and squash them all and by ending them hear "the button colour is wrong"...'

    assert description == tobeDescription


@given(parsers.parse('the user "{new_user}" is a member of group "{group_name}"'))
@then(parsers.parse('user "{new_user}" is now a member of the group "{group_name}"'))
def then_user_is_member(user, new_user, group_name):
    _, body = api_request(
        user,
        "group_user_is_member",
        {"username": new_user,
         "group_name": group_name}
    )

    is_member = body['data']
    assert is_member


@then(parsers.parse('the role of user "{new_user}" in group "{group_name}" is updated'))
def then_user_update_persisted(user, new_user, group_name):
    _, body = api_request(
        user,
        "group_get_user_role",
        {"username": new_user,
         "group_name": group_name}
    )

    role = body["data"]
    assert role == "manager"


@given('the Yoda API for processing csv group data API is queried', target_fixture="api_response")
def api_group_import_csv_data(user):
    header_and_data = "category,subcategory,groupname,manager:manager,member:member1,member:member2,viewer:viewer1\rdefault-2,default-2,csvtestgroup,man1@uu.nl,member1@uu.nl,member2222@uu.nl,blabla@uu.nl"
    return api_request(
        user,
        "group_process_csv",
        {"csv_header_and_data": header_and_data,
         "allow_update": True,
         "delete_users": True}
    )
