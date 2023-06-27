# coding=utf-8
"""Schema API feature tests."""

__copyright__ = 'Copyright (c) 2022-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import api_request

scenarios('../../features/api/api_schema.feature')


@given('the Yoda schema get schemas API is queried', target_fixture="api_response")
def api_group_data(user):
    return api_request(
        user,
        "schema_get_schemas",
        {}
    )


@then(parsers.parse('schema {schema} exists'))
def schema_exists(api_response, schema):
    _, body = api_response

    assert body['data']['schemas']
    assert schema in body['data']['schemas']


@then(parsers.parse('default schema is present'))
def default_schema_present(api_response):
    _, body = api_response

    assert body['data']['schemas']
    assert body['data']['schema_default']

    # Ensure that default schema actually exists.
    assert body['data']['schema_default'] in body['data']['schemas']
