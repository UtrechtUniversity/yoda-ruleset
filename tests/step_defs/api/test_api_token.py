# coding=utf-8
"""Token API feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_token.feature')


@given(parsers.parse("the Yoda token generate API is queried with {label}"), target_fixture="api_response")
def api_token_generate(user, label):
    return api_request(
        user,
        "token_generate",
        {"label": label}
    )


@given('the Yoda token load API is queried', target_fixture="api_response")
def api_token_load(user):
    return api_request(
        user,
        "token_load",
        {}
    )


@given(parsers.parse("the Yoda token delete API is queried with {label}"), target_fixture="api_response")
def api_token_delete(user, label):
    return api_request(
        user,
        "token_delete",
        {"label": label}
    )


@then('all tokens are returned')
def api_attribute_value(api_response):
    _, body = api_response
    tokens = [token['label'] for token in body['data']]

    valid_tokens = ['api_test_token_1',
                    'api_test_token_2',
                    'api_test_token_3',
                    'api_test_token_4',
                    'api_test_token_5']

    for token in valid_tokens:
        if token not in tokens:
            assert False
