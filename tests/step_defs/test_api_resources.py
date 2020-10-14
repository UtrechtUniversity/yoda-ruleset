# coding=utf-8
"""Resources API feature tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session>
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../features/api_resources.feature')


@given('the Yoda resources API is queried for all research groups of current datamanager', target_fixture="api_response")
def api_get_groups_of_datamanger():
    return api_request(
        "resource_groups_dm",
        {}
    )


@then('"<group>" for datamanager are found')
def api_response_groups_for_datamanager(api_response, group):
    _, body = api_response

    assert len(body["data"]) > 0
    found_group = False
    for list in body["data"]:
        if group in list:
            found_group = True
            break

    assert found_group


@given('the Yoda resources API is queried by a datamanager for monthly storage data', target_fixture="api_response")
def api_get_monthly_stats_dm():
    return api_request(
        "resource_monthly_stats_dm",
        {}
    )


@then('monthly storage data for a datamanager is found')
def api_response_monthly_storage_for_dm(api_response):
    _, body = api_response

    # check presence all keys
    assert body["data"][0]["category"]
    assert body["data"][0]["tier"]
    assert body["data"][0]["storage"]


@given('the Yoda resources API is queried by a for statistics data to be used as a feed for an export file', target_fixture="api_response")
def api_get_monthly_category_stats_export_dm():
    return api_request(
        "resource_monthly_category_stats_export_dm",
        {}
    )


@then('storage data for export is found')
def api_response_storage_data_for_export(api_response):
    _, body = api_response

    assert body["data"][0]["category"]
    assert body["data"][0]["subcategory"]
    assert body["data"][0]["storage"]
    assert body["data"][0]["month"]
    assert body["data"][0]["groupname"]
    assert body["data"][0]["tier"]


@given('the Yoda resources API is queried for all monthly statistics', target_fixture="api_response")
def api_monthly_stats():
    return api_request(
        "resource_monthly_stats",
        {}
    )


@then('rodsadmin monthly statistics is found')
def api_response_monthly_statistics_rodsadmin(api_response):
    _, body = api_response

    assert body['data'][0]['category']
    assert body['data'][0]['tier']
    assert body['data'][0]['storage']


@given('the Yoda resources API is queried for all resources and tiers', target_fixture="api_response")
def api_resource_and_tier_data():
    return api_request(
        "resource_resource_and_tier_data",
        {}
    )


@then('list of resources and tiers is found')
def api_response_list_of_resources_and_tiers(api_response):
    _, body = api_response

    # {'tier': 'Standard', 'name': 'dev001_2', 'id': '10018'}
    assert body['data'][0]['tier']
    assert body['data'][0]['name']
    assert body['data'][0]['id']


@given('the Yoda resources API is queried for tier_name of "<resource_name>"', target_fixture="api_response")
def api_get_tier_on_resource(resource_name):
    return api_request(
        "resource_tier",
        {"res_name": resource_name}
    )


@then('"<tier_name>" is found')
def api_response_tier_name_for_resource(api_response, tier_name):
    _, body = api_response

    assert body['data'] == tier_name


@given('the Yoda resources API is queried for all available tiers', target_fixture="api_response")
def api_get_tiers():
    return api_request(
        "resource_get_tiers",
        {}
    )


@then('list with "<tier_name>" is found')
def api_response_all_tiers(api_response, tier_name):
    _, body = api_response

    assert tier_name in body['data']


@given('the Yoda resources API is requested to save tier "<tier_name>" for resource "<resource_name>"', target_fixture="api_response")
def api_save_tier_for_resource(resource_name, tier_name):
    return api_request(
        "resource_save_tier",
        {"resource_name": resource_name, "tier_name": tier_name}
    )


@then('tier is saved successfully for resource')
def api_response_save_tier_name_successful(api_response):
    _, body = api_response

    assert body['status'] == 'ok'


@given('the Yoda resources API is queried for usertype of current user', target_fixture="api_response")
def api_get_user_type():
    return api_request(
        "resource_user_get_type",
        {}
    )


@then('"<user_type>" is found')
def api_response_user_type(api_response, user_type):
    _, body = api_response

    assert body["data"] == user_type


@given('the Yoda resources API is queried for research groups of current user', target_fixture="api_response")
def api_get_user_research_groups():
    return api_request(
        "resource_user_research_groups",
        {}
    )


@then('"<research_group>" are found for current user')
def api_response_research_groups_for_user(api_response, research_group):
    _, body = api_response

    assert research_group in body["data"]


@given('the Yoda resources API is queried to know if current user is datamanager', target_fixture="api_response")
def api_is_user_datamanager():
    return api_request(
        "resource_user_is_datamanager",
        {}
    )


@then('current user is found')
def api_response_user_is_datamanager(api_response):
    _, body = api_response

    assert body["data"] == 'yes'


@given('the Yoda resources API is queried for full year of monthly data for group "<group_name>" starting from month "<current_month>" backward', target_fixture="api_response")
def api_get_monthly_user_research_groups(group_name, current_month):
    return api_request(
        "resource_full_year_group_data",
        {"group_name": group_name, "current_month": int(current_month)}
    )


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


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response

    assert http_status == code


@then('result "<result>" is found')
def api_response_contents(api_response, result):
    _, body = api_response

    assert len(body['data']['items']) > 0

    # Check expected result is in search results.
    found = False
    for item in body['data']['items']:
        print(item)
        if item["main_original_dataname"] == result:
            found = True
            break

    assert found
