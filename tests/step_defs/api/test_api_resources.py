# coding=utf-8
"""Resources API feature tests."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_resources.feature')


@given('the Yoda resources browse group data API is queried', target_fixture="api_response")
def api_get_groups_paginated_datamanger(user):
    return api_request(
        user,
        "resource_browse_group_data",
        {}
    )


@then(parsers.parse("group {group} is found"))
def api_response_paginated_group_is_found(api_response, group):
    _, body = api_response

    assert len(body["data"]["items"]) > 0

    found_group = False

    for item in body["data"]["items"]:
        if item["name"] == group:
            found_group = True
            break

    assert found_group


@given(parsers.parse("the Yoda resources API is queried for a paginated range of research groups filtered on group {group}"), target_fixture="api_response")
def api_get_groups_paginated_filtered(user, group):
    return api_request(
        user,
        "resource_browse_group_data",
        {"search_groups": group}
    )


@then("only 1 group is found")
def api_response_paginated_group_found_one(api_response):
    _, body = api_response

    assert len(body["data"]["items"]) == 1


@given(parsers.parse("the Yoda resources full year group data API is queried with {group}"), target_fixture="api_response")
def api_resource_full_year_group_data(user, group):
    return api_request(
        user,
        "resource_full_year_group_data",
        {'group_name': group}
    )


@then('monthly storage data for group is found')
def api_response_monthly_storage_for_group(api_response):
    _, body = api_response

    assert body["data"]["months"]
    assert body["data"]["tiers"]
    assert body["data"]["total_storage"]


@then('monthly storage data for a datamanager is found')
def api_response_monthly_storage_for_dm(api_response):
    _, body = api_response

    # check presence all keys
    assert body["data"][0]["category"]
    assert body["data"][0]["tier"]
    assert body["data"][0]["storage"]


@given('the Yoda resources monthly category stats API is queried', target_fixture="api_response")
def api_get_monthly_category_stats_export_dm(user):
    return api_request(
        user,
        "resource_monthly_category_stats",
        {}
    )


@then('storage data for export is found')
def api_response_storage_data_for_export(api_response):
    _, body = api_response

    assert body["data"][0]["category"]
    assert body["data"][0]["subcategory"]
    assert body["data"][0]["storage"]
    assert body["data"][0]["groupname"]
    assert body["data"][0]["tier"]


@given('the Yoda resources category stats API is queried', target_fixture="api_response")
def api_monthly_stats(user):
    return api_request(
        user,
        "resource_category_stats",
        {}
    )


@then('category statistics are found')
def api_response_category_statistics_found(api_response):
    _, body = api_response

    assert body['data'][0]['category']
    assert body['data'][0]['storage']


@then('full year storage data is found')
def api_response_full_year_storage(api_response):
    _, body = api_response

    # A list of dicts like following
    # [{'month=10-tier=Standard': 6772}]

    # Look at first entry
    storage_month_data = body['data'][0]
    for key in storage_month_data:
        assert 'month=' in key
        break
