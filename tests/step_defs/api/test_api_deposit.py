# coding=utf-8
"""Deposit API feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_deposit.feature')


@given('the Yoda deposit path API is queried', target_fixture="api_response")
def api_deposit_path(user):
    return api_request(
        user,
        "deposit_path",
        {}
    )

@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, body = api_response
    assert http_status == code


# @then('metadata is returned for "<collection>"')
# def metadata_returned(api_response, collection):
#     http_status, body = api_response
#     assert http_status == 200


# @given('a file "<file>" is uploaded in "<folder>"', target_fixture="api_response")
# def api_deposit_file_upload(user, file, folder):
#     return post_form_data(
#         user,
#         "research/browse/upload",
#         {"file": (file, "test"), "filepath": (None, folder)}
#     )

# @then('deposit path is returned')
# def api_response_contents(api_response):
#     _, body = api_response
#     assert len(body['data']['deposit_path']) > 0
#     assert body['data']['deposit_path'] == "research-initial"
