# coding=utf-8
"""Schema transformations API feature tests."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then
)

from conftest import api_request, upload_data

scenarios('../../features/api/api_schema_transformations.feature')


@given(parsers.parse("a metadata file with schema {schema_from} is uploaded to folder with schema {schema_to}"), target_fixture="api_response")
def api_upload_transform_metadata_json(user, schema_from, schema_to):
    api_request(
        user,
        "research_file_delete",
        {"coll": f"/tempZone/home/research-{schema_to}", "file_name": "yoda-metadata.json"}
    )

    cwd = os.getcwd()

    with open(f"{cwd}/files/transformations/{schema_from}_{schema_to}.json", "rb") as f:
        metadata = f.read()

    return upload_data(
        user,
        "yoda-metadata.json",
        f"/research-{schema_to}",
        metadata
    )


@then(parsers.parse("transformation of metadata is successful for collection {schema_to}"), target_fixture="api_response")
def api_transform_metadata(user, schema_to):
    collection = f'/tempZone/home/research-{schema_to}'

    return api_request(
        user,
        "transform_metadata",
        {"coll": collection}
    )
