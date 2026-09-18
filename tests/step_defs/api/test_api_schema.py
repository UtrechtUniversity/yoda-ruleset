# coding=utf-8
"""Schema API feature tests."""

__copyright__ = 'Copyright (c) 2022-2026, Utrecht University'
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
def api_schema_get_schemas(user):
    return api_request(
        user,
        "schema_get_schemas",
        {}
    )


@given('the Yoda schema get building blocks schemas API is queried', target_fixture="api_response")
def api_schema_get_building_blocks(user):
    return api_request(
        user,
        "schema_get_building_blocks",
        {}
    )


@given('the Yoda schema get composed schemas API is queried', target_fixture="api_response")
def api_schema_get_composed_schemas(user):
    return api_request(
        user,
        "schema_get_composed_schemas",
        {}
    )


@given(parsers.parse('the Yoda schema get composed schema API is queried with {identifier}'), target_fixture="api_response")
def api_schema_get_composed_schema(user, identifier):
    return api_request(
        user,
        "schema_get_composed_schema",
        {"identifier": identifier}
    )


@given(parsers.parse('the Yoda schema post composed schemas API is queried with {identifier}'), target_fixture="api_response")
def api_schema_post_composed_schema(user, identifier):
    return api_request(
        user,
        "schema_post_composed_schema",
        {"identifier": identifier, "blocks": ["descriptive_1-0-0", "citation_1-0-0", "preservation_1-0-0", "access-rights_1-0-0"]}
    )


@given(parsers.parse('the Yoda schema put composed schemas API is queried with {identifier}'), target_fixture="api_response")
def api_schema_put_composed_schema(user, identifier):
    return api_request(
        user,
        "schema_put_composed_schema",
        {"identifier": identifier, "blocks": ["descriptive_1-0-0", "citation_1-0-0", "preservation_1-0-0", "access-rights_1-0-0"]}
    )


@given(parsers.parse('the Yoda schema delete composed schemas API is queried with {identifier}'), target_fixture="api_response")
def api_schema_delete_composed_schema(user, identifier):
    return api_request(
        user,
        "schema_delete_composed_schema",
        {"identifier": identifier}
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


@then(parsers.parse('list contains schema {schema}'))
def list_contains_schema(api_response, schema):
    _, body = api_response

    assert body['data']
    assert any(item['name'] == schema for item in body['data'])


@then(parsers.parse('building block {block} is present'))
def building_block_present(api_response, block):
    _, body = api_response

    assert body['data']
    assert block in body['data']


@then(parsers.parse('schema contains building block {block}'))
def schema_contains_building_block(api_response, block):
    _, body = api_response

    assert body['data']['blocks']
    assert block in body['data']['blocks']
