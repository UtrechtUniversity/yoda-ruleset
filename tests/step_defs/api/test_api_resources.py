# coding=utf-8
"""Resources API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_resources.feature')


@given('the Yoda resources API is queried for all research groups', target_fixture="api_response")
def api_get_groups_of_datamanger(user):
    return api_request(
        user,
        "resource_list_groups",
        {}
    )


@then('"<group>" is found')
def api_response_group_is_found(api_response, group):
    _, body = api_response

    assert len(body["data"]) > 0
    found_group = False
    for list in body["data"]:
        if group in list:
            found_group = True
            break

    assert found_group


@given('the Yoda resources full year group data API is queried with "<group>"', target_fixture="api_response")
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
    assert body['data'][0]['tier']
    assert body['data'][0]['storage']


@given('the Yoda resources API is queried for all resources and tiers', target_fixture="api_response")
def api_resource_and_tier_data(user):
    return api_request(
        user,
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
def api_get_tier_on_resource(user, resource_name):
    return api_request(
        user,
        "resource_tier",
        {"res_name": resource_name}
    )


@then('"<tier_name>" is found')
def api_response_tier_name_for_resource(api_response, tier_name):
    _, body = api_response

    assert body['data'] == tier_name


@given('the Yoda resources API is queried for all available tiers', target_fixture="api_response")
def api_get_tiers(user):
    return api_request(
        user,
        "resource_get_tiers",
        {}
    )


@then('list with "<tier_name>" is found')
def api_response_all_tiers(api_response, tier_name):
    _, body = api_response

    assert tier_name in body['data']


@given('the Yoda resources API is requested to save tier "<tier_name>" for resource "<resource_name>"', target_fixture="api_response")
def api_save_tier_for_resource(user, resource_name, tier_name):
    return api_request(
        user,
        "resource_save_tier",
        {"resource_name": resource_name, "tier_name": tier_name}
    )


@then('tier is saved successfully for resource')
def api_response_save_tier_name_successful(api_response):
    _, body = api_response

    assert body['status'] == 'ok'


@given('the Yoda resources API is queried for full year of monthly data for group "<group_name>" starting from current month backward', target_fixture="api_response")
def api_get_monthly_user_research_groups(user, group_name):
    from datetime import datetime
    current_month = datetime.now().month

    return api_request(
        user,
        "resource_full_year_group_data",
        {"group_name": group_name, "current_month": current_month}
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
