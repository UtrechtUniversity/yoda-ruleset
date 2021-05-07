# coding=utf-8
"""Datarequest API feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request, post_form_data

scenarios('../../features/api/api_datarequest.feature')


@given('the Yoda datarequest browse API is queried', target_fixture="api_response")
def api_datarequest_browse(user):
    return api_request(
        user,
        "datarequest_browse",
        {}
    )


@given('the Yoda datarequest schema get API is queried with schema name "<schema_name>"', target_fixture="api_response")
def api_datarequest_schema_get(user, schema_name):
    return api_request(
        user,
        "datarequest_schema_get",
        {"schema_name": schema_name}
    )


@given('the Yoda datarequest submit API is queried with a data request to save as draft', target_fixture="api_response")
def api_datarequest_save(user):
    return api_request(
        user,
        "datarequest_submit",
        {
            "data": {
                "introduction": {},
                "contact": {
                    "given_name": "test",
                    "family_name": "test",
                    "institution": "test",
                    "department": "test",
                    "academic_role": "test",
                    "work_address": "test",
                    "phone": "test"
                },
                "datarequest": {
                    "data": {
                        "selectedRows": [
                            {
                                "expId": 2,
                                "expCohort": 1,
                                "expWave": 8,
                                "expType": 0,
                                "expSubject": 0,
                                "expName": 5,
                                "expInfo": "",
                                "expAdditionalRemarks": ""
                            }
                        ]
                    },
                    "study_information": {
                        "title": "test",
                        "attachments": "Yes",
                        "research_questions": "test",
                        "hypotheses": "test"
                    },
                    "variables": {
                        "variables": "test",
                        "unit_of_analysis": "test",
                        "missing_data": "test",
                        "statistical_outliers": "test"
                    },
                    "knowledge_of_data": {
                        "prior_publication": "test",
                        "prior_knowledge": "test"
                    },
                    "analyses": {
                        "statistical_models": "test",
                        "effect_size": "test",
                        "statistical_power": "test",
                        "inference_criteria": "test",
                        "assumption_violation": "test",
                        "reliability_and_robustness_testing": "test",
                        "exploratory_analysis": "test"
                    },
                    "contribution": {
                        "contribution_time": "No",
                        "contribution_financial": "No",
                        "contribution_favor": "Yes",
                        "contribution_favor_description": "test"
                    },
                    "purpose": "Analyses in order to publish",
                    "publication_type": "Article or report",
                    "publication_approval": True
                },
                "owner": "researcher"
            },
            "draft": True
        })


@given('datarequest exists', target_fixture="datarequest_id")
def datarequest_exists(user):
    http_status, body = api_request(
        user,
        "datarequest_browse",
        {"sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0

    return body["data"]["items"][0]["id"]


@given('the Yoda datarequest submit API is queried with a draft data request to submit', target_fixture="api_response")
def api_datarequest_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_submit",
        {
            "data": {
                "introduction": {},
                "contact": {
                    "given_name": "test",
                    "family_name": "test",
                    "institution": "test",
                    "department": "test",
                    "academic_role": "test",
                    "work_address": "test",
                    "phone": "test"
                },
                "datarequest": {
                    "data": {
                        "selectedRows": [
                            {
                                "expId": 2,
                                "expCohort": 1,
                                "expWave": 8,
                                "expType": 0,
                                "expSubject": 0,
                                "expName": 5,
                                "expInfo": "",
                                "expAdditionalRemarks": ""
                            }
                        ]
                    },
                    "study_information": {
                        "title": "test",
                        "attachments": "Yes",
                        "research_questions": "test",
                        "hypotheses": "test"
                    },
                    "variables": {
                        "variables": "test",
                        "unit_of_analysis": "test",
                        "missing_data": "test",
                        "statistical_outliers": "test"
                    },
                    "knowledge_of_data": {
                        "prior_publication": "test",
                        "prior_knowledge": "test"
                    },
                    "analyses": {
                        "statistical_models": "test",
                        "effect_size": "test",
                        "statistical_power": "test",
                        "inference_criteria": "test",
                        "assumption_violation": "test",
                        "reliability_and_robustness_testing": "test",
                        "exploratory_analysis": "test"
                    },
                    "contribution": {
                        "contribution_time": "No",
                        "contribution_financial": "No",
                        "contribution_favor": "Yes",
                        "contribution_favor_description": "test"
                    },
                    "purpose": "Analyses in order to publish",
                    "publication_type": "Article or report",
                    "publication_approval": True
                },
                "owner": "researcher"
            },
            "draft": False,
            "draft_request_id": datarequest_id
        })


@given('the Yoda datarequest roles get API is queried with request id', target_fixture="api_response")
def api_datarequest_roles_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_roles_get",
        {"request_id": datarequest_id}
    )


@given('attachment is uploaded', target_fixture="api_response")
def api_datarequest_attachment_upload(user, datarequest_id):
    return post_form_data(
        user,
        "/datarequest/upload_attachment/{}".format(datarequest_id),
        {"file": ("attachment.pdf", "test")}
    )


@given('attachments are submitted', target_fixture="api_response")
def api_datarequest_attachments_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_attachments_submit",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest get API is queried with request id', target_fixture="api_response")
def api_datarequest_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_get",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest preliminary review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_preliminary_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_preliminary_review_submit",
        {"data": {"preliminary_review": "Accepted for data manager review", "internal_remarks": "test"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest preliminary review get API is queried with request id', target_fixture="api_response")
def api_datarequest_preliminary_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_preliminary_review_get",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest datamanager review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_datamanager_review_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_datamanager_review_submit",
        {"data": {"datamanager_review": "Accepted", "datamanager_remarks": "test"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest datamanager review get API is queried with request id', target_fixture="api_response")
def api_datarequest_datamanager_review_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_datamanager_review_get",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest dmr review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_dmr_review_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_dmr_review_submit",
        {"data": {"decision": "Accepted for review", "response_to_dm_remarks": "test"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest dmr review get API is queried with request id', target_fixture="api_response")
def api_datarequest_dmr_review_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_dmr_review_get",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest contribution review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_contribution_review_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_contribution_review_submit",
        {"data": {"decision": "Accepted"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest contribution review get API is queried with request id', target_fixture="api_response")
def api_datarequest_contribution_review_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_contribution_review_get",
        {"request_id": datarequest_id}
    )


@given('the datarequest assignment submit API is queried with request id', target_fixture="api_response")
def api_datarequest_assignment_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_assignment_submit",
        {"data": {"assign_to": ["dmcmember"]}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest assignment get API is queried with request id', target_fixture="api_response")
def api_datarequest_assignment_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_assignment_get",
        {"request_id": datarequest_id}
    )


@given('the datarequest review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_review_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_review_submit",
        {"data": {"biological_samples": True, "for_publishing": True, "evaluation": "Approve", "evaluation_rationale": "i", "biological_samples_volume": "io", "biological_samples_committee_approval": "i", "contribution": "i", "informed_consent_fit": "i", "research_question_answerability": "i", "study_quality": "i", "logistical_feasibility": "i", "study_value": "i", "researcher_expertise": "i", "username": "dmcmember"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest reviews get API is queried with request id', target_fixture="api_response")
def api_datarequest_reviews_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_reviews_get",
        {"request_id": datarequest_id}
    )


@given('the datarequest evaluation submit API is queried with request id', target_fixture="api_response")
def api_datarequest_evaluation_submit(user, datarequest_id):
    return api_request(
        user,
        "datarequest_evaluation_submit",
        {"data": {"evaluation": "Approved"}, "request_id": datarequest_id}
    )


@given('the datarequest contribution confirm API is queried with request id', target_fixture="api_response")
def api_datarequest_contribution_confirm(user, datarequest_id):
    return api_request(
        user,
        "datarequest_contribution_confirm",
        {"request_id": datarequest_id}
    )


@given('the datarequest feedback get API is queried with request id', target_fixture="api_response")
def api_datarequest_feedback_get(user, datarequest_id):
    return api_request(
        user,
        "datarequest_feedback_get",
        {"request_id": datarequest_id}
    )


@given('DTA is uploaded', target_fixture="api_response")
def api_datarequest_dta_upload(user, datarequest_id):
    return post_form_data(
        user,
        "/datarequest/upload_dta/{}".format(datarequest_id),
        {"file": ("dta.pdf", "test")}
    )


@given('signed DTA is uploaded', target_fixture="api_response")
def api_datarequest_signed_dta_upload(user, datarequest_id):
    return post_form_data(
        user,
        "/datarequest/datarequest/upload_signed_dta/{}".format(datarequest_id),
        {"file": ("signed_dta.pdf", "test")}
    )


@given('the datarequest data ready API is queried with request id', target_fixture="api_response")
def api_datarequest_data_ready(user, datarequest_id):
    return api_request(
        user,
        "datarequest_data_ready",
        {"request_id": datarequest_id}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@then(parsers.parse('request status is "{status}"'))
def request_status(user, datarequest_id, status):
    _, body = api_request(
        user,
        "datarequest_get",
        {"request_id": datarequest_id}
    )

    assert len(body['data']) > 0
    assert body['data']['requestStatus'] == status


@then('the result is "<result>"')
def result_is(api_response, result):
    _, body = api_response

    assert str(body['data']) == result
