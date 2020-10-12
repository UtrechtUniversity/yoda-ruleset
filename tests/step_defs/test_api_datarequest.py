# coding=utf-8
"""Datarequest API feature tests.

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

scenarios('../features/api_datarequest.feature')


@given('the Yoda datarequest browse API is queried', target_fixture="api_response")
def api_browse_folder():
    return api_request(
        "datarequest_browse",
        {}
    )


@given('the Yoda datarequest submit API is queried with data', target_fixture="api_response")
def api_datarequest_submit():
    return api_request(
        "datarequest_submit",
        {"data": {
            "introduction": {},
            "researchers": {
                "contacts": [{
                    "name": "test",
                    "institution": "test",
                    "department": "test",
                    "email": "test",
                    "work_address": "test",
                    "phone": "test"
                }]
            },
            "research_context": {
                "title": "test",
                "background": "test",
                "research_question": "test",
                "requested_data_summary": "test"
            },
            "hypotheses": {},
            "methods": {
                "design": "test",
                "preparation": "test",
                "processing": "test"
            },
            "datarequest": {
                "data": {
                    "selectedRows": [{
                        "expId": 1,
                        "expCohort": 1,
                        "expWave": 7,
                        "expType": 0,
                        "expSubject": 0,
                        "expName": "Blood",
                        "expInfo": ""
                    }]
                },
                "purpose": "Analyses for data assessment only (results will not be published)",
                "data_lock_notification": True,
                "publication_approval": True
            },
            "contribution": {
                "contribution_time": "No",
                "contribution_financial": "No",
                "contribution_favor": "No"
            }
        }, "previous_request_id": None,
        })


@given('datarequest exists', target_fixture="datarequest_id")
def datarequest_exists():
    http_status, body = api_request(
        "datarequest_browse",
        {"sort_order": "desc"}
    )

    assert http_status == 200
    assert len(body["data"]["items"]) > 0

    return body["data"]["items"][0]["id"]


@given('the Yoda datarequest get API is queried with request id', target_fixture="api_response")
def api_datarequest_get(datarequest_id):
    return api_request(
        "datarequest_get",
        {"request_id": datarequest_id}
    )


@given('the Yoda datarequest preliminary review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_reliminary_submit(datarequest_id):
    return api_request(
        "datarequest_preliminary_review_submit",
        {"data": {"preliminary_review": "Accepted for data manager review", "internal_remarks": "test"}, "request_id": datarequest_id}
    )


@given('the Yoda datarequest datamanager review submit API is queried with request id', target_fixture="api_response")
def api_datarequest_datamanager_submit(datarequest_id):
    return api_request(
        "datarequest_datamanager_review_submit",
        {"data": {"datamanager_review": "Accepted", "datamanager_remarks": "test"}, "request_id": datarequest_id}
    )


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code


@then(parsers.parse('request status is "{status}"'))
def request_status(datarequest_id, status):
    _, body = api_request(
        "datarequest_get",
        {"request_id": datarequest_id}
    )

    assert len(body['data']) > 0
    assert body['data']['requestStatus'] == status
