# coding=utf-8
"""Intake API feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_intake.feature')


@given('the Yoda intake list studies API is queried', target_fixture="api_response")
def api_intake_list_studies(user):
    return api_request(
        user,
        "intake_list_studies",
        {}
    )


@given('the Yoda intake list datamanager studies API is queried', target_fixture="api_response")
def api_intake_list_dm_studies(user):
    return api_request(
        user,
        "intake_list_dm_studies",
        {}
    )


@given('the Yoda intake count total files API is queried with collection "<collection>"', target_fixture="api_response")
def api_intake_count_total_files(user, collection):
    return api_request(
        user,
        "intake_count_total_files",
        {"coll": collection}
    )


@given('the Yoda intake list unrecognized files API is queried with collection "<collection>"', target_fixture="api_response")
def api_intake_list_unrecognized_files(user, collection):
    return api_request(
        user,
        "intake_list_unrecognized_files",
        {"coll": collection}
    )


@given('the Yoda intake list datasets API is queried with collection "<collection>"', target_fixture="api_response")
def api_intake_list_datasets(user, collection):
    return api_request(
        user,
        "intake_list_datasets",
        {"coll": collection}
    )


@given('the Yoda intake scan for datasets API is queried with collection "<collection>"', target_fixture="api_response")
def api_intake_scan_for_datasets(user, collection):
    return api_request(
        user,
        "intake_scan_for_datasets",
        {"coll": collection}
    )


@given('the Yoda intake lock API is queried with dataset id and collection "<collection>"', target_fixture="api_response")
def api_intake_lock_dataset(user, dataset_id, collection):
    return api_request(
        user,
        "intake_lock_dataset",
        {"path": collection, "dataset_id": dataset_id}
    )


@given('the Yoda intake unlock API is queried with dataset id and collection "<collection>"', target_fixture="api_response")
def api_intake_unlock_dataset(user, dataset_id, collection):
    return api_request(
        user,
        "intake_unlock_dataset",
        {"path": collection, "dataset_id": dataset_id}
    )


@given('the Yoda intake dataset get details API is queried with dataset id and collection "<collection>"', target_fixture="api_response")
def api_intake_dataset_get_details(user, dataset_id, collection):
    return api_request(
        user,
        "intake_dataset_get_details",
        {"coll": collection, "dataset_id": dataset_id}
    )


@given('the Yoda intake dataset add comment API is queried with dataset id, collection "<collection>" and comment "<comment>"', target_fixture="api_response")
def api_intake_dataset_add_comment(user, dataset_id, collection, comment):
    return api_request(
        user,
        "intake_dataset_add_comment",
        {"coll": collection, "dataset_id": dataset_id, "comment": comment}
    )


@given('the Yoda intake report vault dataset counts per study API is queried with study id "<study_id>"', target_fixture="api_response")
def api_intake_report_vault_dataset_counts_per_study(user, study_id):
    return api_request(
        user,
        "intake_report_vault_dataset_counts_per_study",
        {"study_id": study_id}
    )


@given('the Yoda intake report vault aggregated info API is queried with study id "<study_id>"', target_fixture="api_response")
def api_intake_report_vault_aggregated_info(user, study_id):
    return api_request(
        user,
        "intake_report_vault_aggregated_info",
        {"study_id": study_id}
    )


@given('the Yoda intake report export study data API is queried with study id "<study_id>"', target_fixture="api_response")
def api_intake_report_export_study_data(user, study_id):
    return api_request(
        user,
        "intake_report_export_study_data",
        {"study_id": study_id}
    )


@given('dataset exists', target_fixture="dataset_id")
def dataset_exists(user):
    return "dataset id"


@then('study "<study>" is returned')
def study_returned(api_response, study):
    _, body = api_response

    assert study in body['data']


@then('debug')
def debug(api_response):
    _, body = api_response

    assert 0, body
